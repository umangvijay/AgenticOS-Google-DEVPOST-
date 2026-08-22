import json
import logging
from abc import ABC, abstractmethod
from typing import Optional
from backend.models.schedule import Schedule
from google.cloud import scheduler_v1

logger = logging.getLogger(__name__)

class SchedulerClient(ABC):
    @abstractmethod
    def create_job(self, schedule: Schedule, pubsub_topic: str) -> str:
        pass
        
    @abstractmethod
    def pause_job(self, job_name: str) -> None:
        pass
        
    @abstractmethod
    def resume_job(self, job_name: str) -> None:
        pass
        
    @abstractmethod
    def delete_job(self, job_name: str) -> None:
        pass

class InMemorySchedulerClient(SchedulerClient):
    def __init__(self):
        self.jobs = {}
        
    def create_job(self, schedule: Schedule, pubsub_topic: str) -> str:
        job_name = f"projects/mock/locations/mock/jobs/sch-{schedule.schedule_id}"
        self.jobs[job_name] = {
            "schedule": schedule.cron_expression,
            "topic": pubsub_topic,
            "state": "ENABLED"
        }
        return job_name
        
    def pause_job(self, job_name: str) -> None:
        if job_name in self.jobs:
            self.jobs[job_name]["state"] = "PAUSED"
            
    def resume_job(self, job_name: str) -> None:
        if job_name in self.jobs:
            self.jobs[job_name]["state"] = "ENABLED"
            
    def delete_job(self, job_name: str) -> None:
        self.jobs.pop(job_name, None)

class GoogleCloudSchedulerClient(SchedulerClient):
    def __init__(self, project_id: str, location: str):
        self.project_id = project_id
        self.location = location
        self.client = scheduler_v1.CloudSchedulerClient()
        self.parent = f"projects/{project_id}/locations/{location}"

    def create_job(self, schedule: Schedule, pubsub_topic: str) -> str:
        payload = json.dumps({"schedule_id": schedule.schedule_id}).encode("utf-8")
        
        job = {
            "name": f"{self.parent}/jobs/sch-{schedule.schedule_id}",
            "pubsub_target": {
                "topic_name": pubsub_topic,
                "data": payload,
            },
            "schedule": schedule.cron_expression,
            "time_zone": schedule.timezone,
        }
        
        try:
            created_job = self.client.create_job(
                request={"parent": self.parent, "job": job}
            )
            logger.info(f"Created Cloud Scheduler job: {created_job.name}")
            return created_job.name
        except Exception as e:
            logger.error(f"Failed to create Cloud Scheduler job: {e}")
            raise

    def pause_job(self, job_name: str) -> None:
        try:
            self.client.pause_job(request={"name": job_name})
            logger.info(f"Paused Cloud Scheduler job: {job_name}")
        except Exception as e:
            logger.error(f"Failed to pause Cloud Scheduler job {job_name}: {e}")
            raise

    def resume_job(self, job_name: str) -> None:
        try:
            self.client.resume_job(request={"name": job_name})
            logger.info(f"Resumed Cloud Scheduler job: {job_name}")
        except Exception as e:
            logger.error(f"Failed to resume Cloud Scheduler job {job_name}: {e}")
            raise

    def delete_job(self, job_name: str) -> None:
        try:
            self.client.delete_job(request={"name": job_name})
            logger.info(f"Deleted Cloud Scheduler job: {job_name}")
        except Exception as e:
            logger.error(f"Failed to delete Cloud Scheduler job {job_name}: {e}")
            raise
