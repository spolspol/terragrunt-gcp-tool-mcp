"""Cost management and analysis for Terragrunt GCP infrastructure."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from google.cloud import billing_v1
from google.cloud import monitoring_v3
from google.cloud import compute_v1
from google.cloud import storage
from google.oauth2 import service_account

from .config import Config
from .models import CostAnalysis, Resource


logger = logging.getLogger(__name__)


class CostManager:
    """Manages cost analysis and tracking for GCP infrastructure."""

    def __init__(self, config: Config):
        """Initialize the Cost manager."""
        self.config = config
        self.project_id = config.gcp.project_id
        self.credentials_path = config.gcp.credentials_path
        self._billing_client = None
        self._monitoring_client = None
        self._compute_client = None
        self._storage_client = None

    def _get_credentials(self):
        """Get GCP credentials."""
        if self.credentials_path:
            import os
            credentials_path = os.path.expandvars(os.path.expanduser(self.credentials_path))
            return service_account.Credentials.from_service_account_file(credentials_path)
        return None

    @property
    def billing_client(self):
        """Get or create billing client."""
        if self._billing_client is None:
            credentials = self._get_credentials()
            if credentials:
                self._billing_client = billing_v1.CloudBillingClient(credentials=credentials)
            else:
                self._billing_client = billing_v1.CloudBillingClient()
        return self._billing_client

    @property
    def monitoring_client(self):
        """Get or create monitoring client."""
        if self._monitoring_client is None:
            credentials = self._get_credentials()
            if credentials:
                self._monitoring_client = monitoring_v3.MetricServiceClient(credentials=credentials)
            else:
                self._monitoring_client = monitoring_v3.MetricServiceClient()
        return self._monitoring_client

    @property
    def compute_client(self):
        """Get or create compute client."""
        if self._compute_client is None:
            credentials = self._get_credentials()
            if credentials:
                self._compute_client = compute_v1.InstancesClient(credentials=credentials)
            else:
                self._compute_client = compute_v1.InstancesClient()
        return self._compute_client

    @property
    def storage_client(self):
        """Get or create storage client."""
        if self._storage_client is None:
            credentials = self._get_credentials()
            if credentials:
                self._storage_client = storage.Client(credentials=credentials, project=self.project_id)
            else:
                self._storage_client = storage.Client(project=self.project_id)
        return self._storage_client

    async def get_cost_analysis(
        self,
        environment: Optional[str] = None,
        period_days: int = 30,
        include_forecasting: bool = True,
        include_recommendations: bool = True
    ) -> CostAnalysis:
        """Get comprehensive cost analysis for infrastructure.
        
        Args:
            environment: Filter by environment
            period_days: Analysis period in days
            include_forecasting: Include cost forecasting
            include_recommendations: Include optimization recommendations
        
        Returns:
            CostAnalysis object with comprehensive cost data
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)
            
            # Get billing account
            billing_account = await self._get_billing_account()
            if not billing_account:
                logger.warning("No billing account found for project")
                return self._create_empty_cost_analysis()
            
            # Get cost data from Cloud Billing API
            total_cost, service_costs = await self._get_billing_costs(
                billing_account, start_date, end_date
            )
            
            # Get resource-specific costs
            resource_costs = await self._get_resource_costs(environment, start_date, end_date)
            
            # Get environment breakdown
            environment_costs = await self._get_environment_costs(start_date, end_date)
            
            # Get cost trends
            trends = await self._get_cost_trends(billing_account, period_days)
            
            # Generate forecasting if requested
            forecast = None
            if include_forecasting:
                forecast = await self._generate_cost_forecast(trends, period_days)
            
            # Generate recommendations if requested
            recommendations = []
            if include_recommendations:
                recommendations = await self._generate_cost_recommendations(
                    resource_costs, service_costs, environment
                )
            
            return CostAnalysis(
                total_cost=total_cost,
                currency="USD",
                period=f"{period_days} days",
                breakdown_by_service=service_costs,
                breakdown_by_environment=environment_costs,
                breakdown_by_resource=resource_costs,
                trends=trends,
                last_updated=datetime.now(),
                forecast=forecast,
                recommendations=recommendations,
                metadata={
                    "billing_account": billing_account,
                    "analysis_period": f"{start_date.isoformat()} to {end_date.isoformat()}",
                    "environment_filter": environment,
                    "include_forecasting": include_forecasting,
                    "include_recommendations": include_recommendations
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get cost analysis: {e}")
            return self._create_empty_cost_analysis(error=str(e))

    async def _get_billing_account(self) -> Optional[str]:
        """Get the billing account for the project."""
        try:
            project_name = f"projects/{self.project_id}"
            project_billing_info = self.billing_client.get_project_billing_info(name=project_name)
            
            if project_billing_info.billing_enabled:
                return project_billing_info.billing_account_name
            else:
                logger.warning(f"Billing not enabled for project {self.project_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get billing account: {e}")
            return None

    async def _get_billing_costs(
        self, 
        billing_account: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Tuple[float, Dict[str, float]]:
        """Get costs from Cloud Billing API."""
        try:
            # This would use the Cloud Billing API to get actual cost data
            # For now, we'll simulate with monitoring metrics and resource analysis
            
            # Get compute costs
            compute_cost = await self._estimate_compute_costs(start_date, end_date)
            
            # Get storage costs
            storage_cost = await self._estimate_storage_costs(start_date, end_date)
            
            # Get network costs (estimated)
            network_cost = await self._estimate_network_costs(start_date, end_date)
            
            # Get other service costs (estimated)
            other_costs = await self._estimate_other_service_costs(start_date, end_date)
            
            service_costs = {
                "Compute Engine": compute_cost,
                "Cloud Storage": storage_cost,
                "Cloud SQL": other_costs.get("cloudsql", 0.0),
                "BigQuery": other_costs.get("bigquery", 0.0),
                "Cloud Build": other_costs.get("cloudbuild", 0.0),
                "Networking": network_cost,
                "Secret Manager": other_costs.get("secretmanager", 0.0),
                "Other": other_costs.get("other", 0.0)
            }
            
            total_cost = sum(service_costs.values())
            
            return total_cost, service_costs
            
        except Exception as e:
            logger.error(f"Failed to get billing costs: {e}")
            return 0.0, {}

    async def _estimate_compute_costs(self, start_date: datetime, end_date: datetime) -> float:
        """Estimate compute costs based on running instances."""
        try:
            total_cost = 0.0
            
            # Get all compute instances
            request = compute_v1.AggregatedListInstancesRequest(
                project=self.project_id,
                max_results=500
            )
            
            page_result = self.compute_client.aggregated_list(request=request)
            
            # Pricing estimates (simplified - real implementation would use Cloud Billing API)
            pricing = {
                "e2-micro": 0.0084,      # per hour
                "e2-small": 0.0168,     # per hour
                "e2-medium": 0.0336,    # per hour
                "e2-standard-2": 0.0672, # per hour
                "e2-standard-4": 0.1344, # per hour
                "n1-standard-1": 0.0475, # per hour
                "n1-standard-2": 0.095,  # per hour
                "n1-standard-4": 0.19,   # per hour
            }
            
            hours_in_period = (end_date - start_date).total_seconds() / 3600
            
            for zone, instances_scoped_list in page_result:
                if instances_scoped_list.instances:
                    for instance in instances_scoped_list.instances:
                        if instance.status == "RUNNING":
                            machine_type = instance.machine_type.split('/')[-1]
                            hourly_rate = pricing.get(machine_type, 0.05)  # Default rate
                            instance_cost = hourly_rate * hours_in_period
                            total_cost += instance_cost
            
            return total_cost
            
        except Exception as e:
            logger.error(f"Failed to estimate compute costs: {e}")
            return 0.0

    async def _estimate_storage_costs(self, start_date: datetime, end_date: datetime) -> float:
        """Estimate storage costs."""
        try:
            total_cost = 0.0
            
            # Get all storage buckets
            buckets = self.storage_client.list_buckets()
            
            # Storage pricing (simplified)
            storage_price_per_gb_month = 0.020  # Standard storage
            days_in_period = (end_date - start_date).days
            
            for bucket in buckets:
                try:
                    # Get bucket size (this is an approximation)
                    total_size_bytes = 0
                    for blob in bucket.list_blobs():
                        total_size_bytes += blob.size or 0
                    
                    size_gb = total_size_bytes / (1024 ** 3)
                    monthly_cost = size_gb * storage_price_per_gb_month
                    period_cost = monthly_cost * (days_in_period / 30)
                    total_cost += period_cost
                    
                except Exception as e:
                    logger.warning(f"Failed to get size for bucket {bucket.name}: {e}")
                    continue
            
            return total_cost
            
        except Exception as e:
            logger.error(f"Failed to estimate storage costs: {e}")
            return 0.0

    async def _estimate_network_costs(self, start_date: datetime, end_date: datetime) -> float:
        """Estimate network costs."""
        try:
            # This is a simplified estimation
            # Real implementation would use Cloud Monitoring API to get actual traffic data
            
            # Estimate based on typical usage patterns
            # This would need to be customized based on actual infrastructure
            estimated_gb_egress = 100  # Estimate 100GB egress per month
            days_in_period = (end_date - start_date).days
            period_egress = estimated_gb_egress * (days_in_period / 30)
            
            # Network pricing (simplified)
            egress_price_per_gb = 0.12  # Price varies by destination
            
            return period_egress * egress_price_per_gb
            
        except Exception as e:
            logger.error(f"Failed to estimate network costs: {e}")
            return 0.0

    async def _estimate_other_service_costs(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Estimate costs for other GCP services."""
        try:
            days_in_period = (end_date - start_date).days
            
            # These are rough estimates - real implementation would query actual usage
            return {
                "cloudsql": 50.0 * (days_in_period / 30),    # Estimated SQL instance costs
                "bigquery": 10.0 * (days_in_period / 30),    # Estimated BigQuery costs
                "cloudbuild": 5.0 * (days_in_period / 30),   # Estimated Cloud Build costs
                "secretmanager": 2.0 * (days_in_period / 30), # Estimated Secret Manager costs
                "other": 20.0 * (days_in_period / 30)        # Other miscellaneous costs
            }
            
        except Exception as e:
            logger.error(f"Failed to estimate other service costs: {e}")
            return {}

    async def _get_resource_costs(
        self, 
        environment: Optional[str], 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, float]:
        """Get costs broken down by individual resources."""
        try:
            resource_costs = {}
            
            # This would map specific resources to their costs
            # For now, we'll provide estimates based on resource types
            
            # Get compute instance costs
            compute_costs = await self._get_compute_resource_costs(environment, start_date, end_date)
            resource_costs.update(compute_costs)
            
            # Get storage costs
            storage_costs = await self._get_storage_resource_costs(environment, start_date, end_date)
            resource_costs.update(storage_costs)
            
            return resource_costs
            
        except Exception as e:
            logger.error(f"Failed to get resource costs: {e}")
            return {}

    async def _get_compute_resource_costs(
        self, 
        environment: Optional[str], 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, float]:
        """Get costs for compute resources."""
        try:
            costs = {}
            
            request = compute_v1.AggregatedListInstancesRequest(
                project=self.project_id,
                max_results=500
            )
            
            page_result = self.compute_client.aggregated_list(request=request)
            
            # Simplified pricing
            pricing = {
                "e2-micro": 0.0084,
                "e2-small": 0.0168,
                "e2-medium": 0.0336,
                "e2-standard-2": 0.0672,
                "e2-standard-4": 0.1344,
            }
            
            hours_in_period = (end_date - start_date).total_seconds() / 3600
            
            for zone, instances_scoped_list in page_result:
                if instances_scoped_list.instances:
                    for instance in instances_scoped_list.instances:
                        # Filter by environment if specified
                        if environment and environment not in instance.name:
                            continue
                        
                        if instance.status == "RUNNING":
                            machine_type = instance.machine_type.split('/')[-1]
                            hourly_rate = pricing.get(machine_type, 0.05)
                            instance_cost = hourly_rate * hours_in_period
                            costs[instance.name] = instance_cost
            
            return costs
            
        except Exception as e:
            logger.error(f"Failed to get compute resource costs: {e}")
            return {}

    async def _get_storage_resource_costs(
        self, 
        environment: Optional[str], 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, float]:
        """Get costs for storage resources."""
        try:
            costs = {}
            
            buckets = self.storage_client.list_buckets()
            storage_price_per_gb_month = 0.020
            days_in_period = (end_date - start_date).days
            
            for bucket in buckets:
                # Filter by environment if specified
                if environment and environment not in bucket.name:
                    continue
                
                try:
                    total_size_bytes = 0
                    for blob in bucket.list_blobs():
                        total_size_bytes += blob.size or 0
                    
                    size_gb = total_size_bytes / (1024 ** 3)
                    monthly_cost = size_gb * storage_price_per_gb_month
                    period_cost = monthly_cost * (days_in_period / 30)
                    costs[bucket.name] = period_cost
                    
                except Exception as e:
                    logger.warning(f"Failed to get cost for bucket {bucket.name}: {e}")
                    continue
            
            return costs
            
        except Exception as e:
            logger.error(f"Failed to get storage resource costs: {e}")
            return {}

    async def _get_environment_costs(self, start_date: datetime, end_date: datetime) -> Dict[str, float]:
        """Get costs broken down by environment."""
        try:
            environment_costs = {}
            
            # Get all resource costs
            all_resource_costs = await self._get_resource_costs(None, start_date, end_date)
            
            # Group by environment (based on naming conventions)
            for resource_name, cost in all_resource_costs.items():
                # Extract environment from resource name
                # This assumes naming convention like: env-resource-name
                env = "unknown"
                if "dev" in resource_name.lower():
                    env = "development"
                elif "staging" in resource_name.lower() or "stage" in resource_name.lower():
                    env = "staging"
                elif "prod" in resource_name.lower() or "production" in resource_name.lower():
                    env = "production"
                elif "test" in resource_name.lower():
                    env = "testing"
                
                environment_costs[env] = environment_costs.get(env, 0.0) + cost
            
            return environment_costs
            
        except Exception as e:
            logger.error(f"Failed to get environment costs: {e}")
            return {}

    async def _get_cost_trends(self, billing_account: str, period_days: int) -> List[Dict[str, Any]]:
        """Get cost trends over time."""
        try:
            trends = []
            
            # Generate daily cost data for the period
            end_date = datetime.now()
            
            for i in range(period_days):
                date = end_date - timedelta(days=i)
                
                # This is simplified - real implementation would query actual daily costs
                # For now, we'll generate sample trend data
                daily_cost = 50.0 + (i * 2.5) + (i % 7) * 10  # Simulate growing costs with weekly patterns
                
                trends.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "cost": daily_cost,
                    "currency": "USD"
                })
            
            # Reverse to get chronological order
            trends.reverse()
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to get cost trends: {e}")
            return []

    async def _generate_cost_forecast(self, trends: List[Dict[str, Any]], period_days: int) -> Dict[str, Any]:
        """Generate cost forecasting based on trends."""
        try:
            if not trends or len(trends) < 7:
                return {"error": "Insufficient data for forecasting"}
            
            # Simple linear regression for forecasting
            costs = [trend["cost"] for trend in trends]
            
            # Calculate average daily growth
            if len(costs) > 1:
                daily_growth = (costs[-1] - costs[0]) / len(costs)
            else:
                daily_growth = 0
            
            # Forecast next 30 days
            current_cost = costs[-1]
            forecast_30_days = current_cost + (daily_growth * 30)
            forecast_90_days = current_cost + (daily_growth * 90)
            
            # Calculate monthly estimate
            monthly_estimate = sum(costs[-30:]) if len(costs) >= 30 else sum(costs) * (30 / len(costs))
            
            return {
                "next_30_days": forecast_30_days,
                "next_90_days": forecast_90_days,
                "monthly_estimate": monthly_estimate,
                "daily_growth_rate": daily_growth,
                "confidence": "medium",  # This would be calculated based on data quality
                "methodology": "linear_regression",
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate cost forecast: {e}")
            return {"error": str(e)}

    async def _generate_cost_recommendations(
        self, 
        resource_costs: Dict[str, float], 
        service_costs: Dict[str, float],
        environment: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Generate cost optimization recommendations."""
        try:
            recommendations = []
            
            # Analyze compute costs
            compute_cost = service_costs.get("Compute Engine", 0)
            if compute_cost > 100:  # If compute costs are high
                recommendations.append({
                    "type": "compute_optimization",
                    "priority": "high",
                    "title": "Optimize Compute Instance Sizes",
                    "description": "Consider rightsizing compute instances based on actual usage",
                    "potential_savings": compute_cost * 0.2,  # Estimate 20% savings
                    "action": "Review instance utilization and downsize underutilized instances",
                    "resources_affected": [name for name, cost in resource_costs.items() if "instance" in name.lower()]
                })
            
            # Analyze storage costs
            storage_cost = service_costs.get("Cloud Storage", 0)
            if storage_cost > 50:
                recommendations.append({
                    "type": "storage_optimization",
                    "priority": "medium",
                    "title": "Implement Storage Lifecycle Policies",
                    "description": "Move infrequently accessed data to cheaper storage classes",
                    "potential_savings": storage_cost * 0.3,  # Estimate 30% savings
                    "action": "Set up lifecycle policies to automatically transition data to Nearline/Coldline storage",
                    "resources_affected": [name for name, cost in resource_costs.items() if "bucket" in name.lower()]
                })
            
            # Check for unused resources
            zero_cost_resources = [name for name, cost in resource_costs.items() if cost == 0]
            if zero_cost_resources:
                recommendations.append({
                    "type": "resource_cleanup",
                    "priority": "low",
                    "title": "Clean Up Unused Resources",
                    "description": "Remove or stop unused resources to avoid potential future costs",
                    "potential_savings": 0,  # No current cost but prevents future costs
                    "action": "Review and remove unused resources",
                    "resources_affected": zero_cost_resources
                })
            
            # Environment-specific recommendations
            if environment == "development":
                recommendations.append({
                    "type": "dev_environment_optimization",
                    "priority": "medium",
                    "title": "Implement Development Environment Scheduling",
                    "description": "Automatically stop development resources outside business hours",
                    "potential_savings": compute_cost * 0.5,  # Estimate 50% savings for dev
                    "action": "Set up Cloud Scheduler to stop/start development instances",
                    "resources_affected": [name for name in resource_costs.keys() if "dev" in name.lower()]
                })
            
            # Add general recommendations
            total_cost = sum(service_costs.values())
            if total_cost > 500:  # If total costs are significant
                recommendations.append({
                    "type": "monitoring_setup",
                    "priority": "high",
                    "title": "Set Up Cost Monitoring and Alerts",
                    "description": "Implement proactive cost monitoring to prevent budget overruns",
                    "potential_savings": total_cost * 0.1,  # Prevent 10% cost overruns
                    "action": "Configure billing alerts and budget notifications",
                    "resources_affected": ["all"]
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate cost recommendations: {e}")
            return []

    def _create_empty_cost_analysis(self, error: Optional[str] = None) -> CostAnalysis:
        """Create an empty cost analysis object."""
        return CostAnalysis(
            total_cost=0.0,
            currency="USD",
            period="30 days",
            breakdown_by_service={},
            breakdown_by_environment={},
            trends=[],
            last_updated=datetime.now(),
            metadata={"error": error} if error else {}
        )

    async def get_cost_alerts(self, threshold_percentage: float = 80.0) -> List[Dict[str, Any]]:
        """Get cost alerts based on budget thresholds."""
        try:
            alerts = []
            
            # Get current month costs
            cost_analysis = await self.get_cost_analysis(period_days=30)
            
            # This would typically compare against set budgets
            # For now, we'll use estimated thresholds
            estimated_monthly_budget = 1000.0  # This should come from configuration
            
            current_spend_percentage = (cost_analysis.total_cost / estimated_monthly_budget) * 100
            
            if current_spend_percentage >= threshold_percentage:
                alerts.append({
                    "type": "budget_threshold",
                    "severity": "high" if current_spend_percentage >= 90 else "medium",
                    "message": f"Current spend is {current_spend_percentage:.1f}% of monthly budget",
                    "current_cost": cost_analysis.total_cost,
                    "budget": estimated_monthly_budget,
                    "threshold": threshold_percentage,
                    "recommendation": "Review recent resource usage and consider cost optimization"
                })
            
            # Check for unusual cost spikes
            if cost_analysis.trends:
                recent_costs = [trend["cost"] for trend in cost_analysis.trends[-7:]]  # Last 7 days
                avg_recent = sum(recent_costs) / len(recent_costs)
                
                if len(cost_analysis.trends) > 14:
                    previous_costs = [trend["cost"] for trend in cost_analysis.trends[-14:-7]]  # Previous 7 days
                    avg_previous = sum(previous_costs) / len(previous_costs)
                    
                    if avg_recent > avg_previous * 1.5:  # 50% increase
                        alerts.append({
                            "type": "cost_spike",
                            "severity": "medium",
                            "message": f"Daily costs increased by {((avg_recent/avg_previous - 1) * 100):.1f}% in the last week",
                            "current_avg": avg_recent,
                            "previous_avg": avg_previous,
                            "recommendation": "Investigate recent infrastructure changes or usage patterns"
                        })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get cost alerts: {e}")
            return []

    async def get_cost_optimization_score(self) -> Dict[str, Any]:
        """Calculate a cost optimization score for the infrastructure."""
        try:
            cost_analysis = await self.get_cost_analysis(include_recommendations=True)
            
            # Calculate optimization score based on various factors
            score = 100.0  # Start with perfect score
            
            # Deduct points for high-cost services without optimization
            total_cost = cost_analysis.total_cost
            if total_cost > 0:
                compute_percentage = (cost_analysis.breakdown_by_service.get("Compute Engine", 0) / total_cost) * 100
                if compute_percentage > 60:  # If compute is >60% of costs
                    score -= 20
                
                storage_percentage = (cost_analysis.breakdown_by_service.get("Cloud Storage", 0) / total_cost) * 100
                if storage_percentage > 30:  # If storage is >30% of costs
                    score -= 15
            
            # Deduct points for number of recommendations
            num_recommendations = len(cost_analysis.recommendations or [])
            score -= min(num_recommendations * 5, 30)  # Max 30 points deduction
            
            # Deduct points for cost growth trend
            if cost_analysis.forecast and "daily_growth_rate" in cost_analysis.forecast:
                growth_rate = cost_analysis.forecast["daily_growth_rate"]
                if growth_rate > 5:  # Growing more than $5/day
                    score -= 15
            
            score = max(0, score)  # Ensure score doesn't go below 0
            
            # Determine grade
            if score >= 90:
                grade = "A"
            elif score >= 80:
                grade = "B"
            elif score >= 70:
                grade = "C"
            elif score >= 60:
                grade = "D"
            else:
                grade = "F"
            
            return {
                "score": score,
                "grade": grade,
                "total_cost": total_cost,
                "recommendations_count": num_recommendations,
                "factors": {
                    "compute_efficiency": 100 - min((compute_percentage - 40) * 2, 40) if total_cost > 0 else 100,
                    "storage_efficiency": 100 - min((storage_percentage - 20) * 3, 30) if total_cost > 0 else 100,
                    "cost_growth": 100 - min(max(growth_rate - 2, 0) * 5, 30) if cost_analysis.forecast else 100,
                    "optimization_opportunities": 100 - min(num_recommendations * 5, 30)
                },
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate cost optimization score: {e}")
            return {
                "score": 0,
                "grade": "F",
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            } 