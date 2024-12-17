"""Client for interacting with Supabase."""
import logging
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
import asyncio

from supabase import create_client, Client
from src.config.settings import load_settings

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Client for interacting with Supabase."""

    def __init__(self) -> None:
        """Initialize the Supabase client."""
        self.settings = load_settings()
        self.client = create_client(
            self.settings.SUPABASE_URL,
            self.settings.SUPABASE_KEY
        )
        self.logger = logging.getLogger(__name__)
        self.timeout = 10  # Set timeout to 10 seconds

    async def _execute_with_timeout(self, table: str, operation: str, data: Dict[str, Any], unique_key: Optional[str] = None) -> Any:
        """Execute a Supabase operation with timeout and retry logic.
        
        Args:
            table: Name of the table
            operation: Operation type ('upsert' or 'select')
            data: Data to upsert or query parameters
            unique_key: Optional column name to use for upsert conflict resolution
            
        Returns:
            Response from Supabase
            
        Raises:
            TimeoutError: If operation takes too long
            Exception: For other errors
        """
        max_retries = 3
        retry_delay = 1  # Start with 1 second delay
        
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Starting {operation} operation on table {table} (attempt {attempt + 1}/{max_retries})")
                
                # Create the query
                query = self.client.table(table)
                if operation == 'upsert':
                    if unique_key:
                        # First check if record exists
                        existing = query.select("id").eq(unique_key, data.get(unique_key)).execute()
                        if existing.data:
                            # Update existing record
                            query = query.update(data).eq(unique_key, data.get(unique_key))
                        else:
                            # Insert new record
                            query = query.insert(data)
                    else:
                        query = query.insert(data)
                elif operation == 'select':
                    query = query.select("*")
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    asyncio.to_thread(lambda: query.execute()),
                    timeout=self.timeout
                )
                
                self.logger.info(f"Completed {operation} operation on table {table}")
                return result.data if hasattr(result, 'data') else result

            except (asyncio.TimeoutError, Exception) as e:
                if "Server disconnected" in str(e) and attempt < max_retries - 1:
                    self.logger.warning(f"Server disconnected during {operation} operation on table {table}. Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                    
                self.logger.error(f"Error during {operation} operation on table {table}: {str(e)}")
                raise

    async def _get_case_uuid(self, case_id: str) -> Optional[str]:
        """Get case UUID from Supabase.
        
        Args:
            case_id: The case ID
            
        Returns:
            The case UUID if found, None otherwise
        """
        try:
            response = await self.client.table("cases").select("id").eq("external_id", case_id).execute()
            if response.data:
                return response.data[0]["id"]
            return None
        except Exception as e:
            logger.error(f"Error getting case UUID: {e}")
            return None

    async def upsert_case_data(self, case_id: str, case_data: Dict[str, Any], summary: Dict[str, Any]) -> str:
        """Upsert case data to Supabase.
        
        Args:
            case_id: External case ID
            case_data: Full case details from API
            summary: Case summary data from API
            
        Returns:
            str: The UUID of the case in Supabase
        """
        self.logger.info(f"Upserting case data: {case_id}")
        try:
            # Check if case exists
            case_uuid = await self._get_case_uuid(case_id)

            # Create timestamps
            created_at = None
            if case_data.get('created_at'):
                dt = datetime.fromtimestamp(case_data.get('created_at', 0) / 1000)
                created_at = dt.isoformat()

            modified_at = None
            if case_data.get('modified_at'):
                dt = datetime.fromtimestamp(case_data.get('modified_at', 0) / 1000)
                modified_at = dt.isoformat()

            # Prepare case data
            data = {
                'external_id': case_id,
                'title': case_data.get('name', 'Untitled Case'),
                'severity': case_data.get('severity'),
                'status': case_data.get('status'),
                'created_at': created_at,
                'modified_at': modified_at,
                'summary': summary,
                'metadata': {
                    'score': case_data.get('score'),
                    'size': case_data.get('size'),
                    'version': case_data.get('version'),
                    'ticket_id': case_data.get('ticket_id'),
                    'tenant_name': case_data.get('tenant_name'),
                    'assignee': case_data.get('assignee'),
                    'assignee_name': case_data.get('assignee_name'),
                    'created_by': case_data.get('created_by'),
                    'created_by_name': case_data.get('created_by_name'),
                    'modified_by': case_data.get('modified_by'),
                    'modified_by_name': case_data.get('modified_by_name'),
                    'acknowledged': case_data.get('acknowledged'),
                    'closed': case_data.get('closed'),
                    'start_timestamp': case_data.get('start_timestamp'),
                    'end_timestamp': case_data.get('end_timestamp')
                }
            }

            if case_uuid:
                # Update existing case
                data['id'] = case_uuid  # Keep the same ID
                
                # Update without affecting foreign key relationships
                query = self.client.table('cases').update(data).eq('id', case_uuid)
                await asyncio.wait_for(
                    asyncio.to_thread(lambda: query.execute()),
                    timeout=self.timeout
                )
            else:
                # Insert new case
                case_uuid = str(uuid4())
                data['id'] = case_uuid
                query = self.client.table('cases').insert(data)
                await asyncio.wait_for(
                    asyncio.to_thread(lambda: query.execute()),
                    timeout=self.timeout
                )

            self.logger.info(f"Successfully upserted case: {case_id}")
            return case_uuid

        except Exception as e:
            self.logger.error(f"Error upserting case data: {e}")
            raise

    async def upsert_alert_data(self, case_id: str, case_uuid: str, alert_data: Dict[str, Any]) -> None:
        """Upsert alert data to Supabase.
        
        Args:
            case_id: External case ID
            case_uuid: Supabase case UUID
            alert_data: Alert data from API
        """
        try:
            # Create the data structure that matches our schema
            created_at = None
            if alert_data.get('created_at'):
                dt = datetime.fromtimestamp(alert_data.get('created_at', 0) / 1000)
                created_at = dt.isoformat()

            data = {
                'id': str(uuid4()),
                'case_id': case_uuid,  # Foreign key to cases table
                'type': alert_data.get('type'),
                'severity': alert_data.get('severity'),
                'created_at': created_at,
                'metadata': alert_data
            }
            
            # Log the data being upserted
            self.logger.info(f"Upserting alert data for case: {case_id}")
            
            # Upsert to Supabase with timeout
            await self._execute_with_timeout('alerts', 'upsert', data, unique_key='id')

        except Exception as e:
            self.logger.error(f"Error upserting alert data: {e}")
            raise

    async def upsert_activity_data(self, case_id: str, case_uuid: str, activity_data: Dict[str, Any]) -> None:
        """Upsert activity data to Supabase.
        
        Args:
            case_id: External case ID
            case_uuid: Supabase case UUID
            activity_data: Activity data from API
        """
        try:
            # Create analysis result data
            created_at = None
            if activity_data.get('timestamp'):
                dt = datetime.fromtimestamp(activity_data.get('timestamp', 0) / 1000)
                created_at = dt.isoformat()

            data = {
                'id': str(uuid4()),
                'case_id': case_uuid,  # Foreign key to cases table
                'severity_score': self._calculate_severity_score(activity_data),
                'priority_score': self._calculate_priority_score(activity_data),
                'key_indicators': self._extract_key_indicators(activity_data),
                'patterns': self._extract_patterns(activity_data),
                'created_at': created_at,
                'metadata': activity_data
            }
            
            # Log the data being upserted
            self.logger.info(f"Upserting activity data for case: {case_id}")
            
            # Upsert to Supabase with timeout
            await self._execute_with_timeout('activities', 'upsert', data, unique_key='id')

        except Exception as e:
            self.logger.error(f"Error upserting activity data: {e}")
            raise

    async def upsert_decision_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert decision metrics into the database.

        Args:
            metrics: The metrics to insert/update

        Returns:
            The upserted record
        """
        try:
            # Try to upsert the metrics
            response = await self.client.table("decision_metrics").upsert(metrics).execute()
            return response.data[0]
        except Exception as e:
            if "does not exist" in str(e):
                # Table doesn't exist, create it
                await self.create_decision_metrics_table()
                # Retry the upsert
                response = await self.client.table("decision_metrics").upsert(metrics).execute()
                return response.data[0]
            raise

    async def create_decision_metrics_table(self):
        """Create the decision metrics table if it doesn't exist."""
        try:
            # Create table using Supabase's native methods
            await self.client.table("decision_metrics").upsert({
                "id": "test",
                "case_id": "test",
                "created_at": datetime.now().isoformat(),
                "decision_type": "test",
                "decision_value": "test",
                "confidence": 0.0,
                "model": "test",
                "prompt": "test",
                "completion": "test"
            })
            logger.info("Successfully created decision_metrics table")
        except Exception as e:
            logger.error(f"Error creating decision_metrics table: {e}")
            raise

    async def upsert_observable_data(self, case_id: str, case_uuid: str, observable_data: Dict[str, Any]) -> None:
        """Upsert observable data to Supabase.
        
        Args:
            case_id: External case ID
            case_uuid: Supabase case UUID
            observable_data: Observable data from API
        """
        try:
            # Create the data structure that matches our schema
            created_at = None
            if observable_data.get('created_at'):
                dt = datetime.fromtimestamp(observable_data.get('created_at', 0) / 1000)
                created_at = dt.isoformat()

            data = {
                'id': str(uuid4()),
                'case_id': case_uuid,  # Foreign key to cases table
                'type': observable_data.get('type'),
                'value': observable_data.get('value'),
                'created_at': created_at,
                'metadata': {
                    'source': observable_data.get('source'),
                    'reputation': observable_data.get('reputation', 'unknown'),
                    'tags': observable_data.get('tags', [])
                }
            }
            
            # Log the data being upserted
            self.logger.info(f"Upserting observable data for case: {case_id}")
            
            # Upsert to Supabase with timeout
            await self._execute_with_timeout('observables', 'upsert', data)

        except Exception as e:
            self.logger.error(f"Error upserting observable data: {e}")
            raise

    async def update(self, table: str, data: Dict[str, Any], match_column: str, match_value: Any) -> None:
        """Update records in a table.
        
        Args:
            table: Name of the table
            data: Data to update
            match_column: Column to match on
            match_value: Value to match
        """
        await self._execute_with_timeout(
            table,
            "upsert",
            data,
            unique_key=match_column
        )

    def _calculate_severity_score(self, activity_data: Dict[str, Any]) -> float:
        """Calculate severity score based on activity data."""
        base_score = 5.0  # Default medium severity
        
        # Adjust based on activity type
        if activity_data.get('type') == 'alert':
            severity = activity_data.get('severity', '').lower()
            if severity == 'critical':
                base_score = 9.0
            elif severity == 'high':
                base_score = 7.0
            elif severity == 'medium':
                base_score = 5.0
            elif severity == 'low':
                base_score = 3.0
                
        return base_score

    def _calculate_priority_score(self, activity_data: Dict[str, Any]) -> float:
        """Calculate priority score based on activity data."""
        base_score = 5.0  # Default medium priority
        
        # Adjust based on activity details
        if 'details' in activity_data:
            details = activity_data['details']
            
            # Increase score for critical activities
            if details.get('is_critical'):
                base_score += 2.0
                
            # Adjust based on impact
            impact = details.get('impact', '').lower()
            if impact == 'high':
                base_score += 1.5
            elif impact == 'medium':
                base_score += 0.5
                
        return min(10.0, base_score)  # Cap at 10.0

    def _extract_key_indicators(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key indicators from activity data."""
        return {
            'type': activity_data.get('type'),
            'action': activity_data.get('action'),
            'user': activity_data.get('user'),
            'source': activity_data.get('source')
        }

    def _extract_patterns(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract patterns from activity data."""
        return {
            'frequency': activity_data.get('frequency'),
            'related_events': activity_data.get('related_events', []),
            'common_factors': activity_data.get('common_factors', {})
        }
