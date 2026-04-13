# Learning Roadmap Generator

## Overview
The Learning Roadmap Generator transforms identified skill gaps into a structured, time-bound educational path.

## Logic Components

### 1. Skill Clustering
Identifies related gaps to create efficient learning modules. For example, if "Docker" and "Kubernetes" are both missing, they are clustered into a "Containerization" module.

### 2. Priority Ordering
Sorts learning modules based on:
1. **Criticality**: Is it a P1 gap?
2. **Dependency**: Can Skill B be learned before Skill A? (e.g., Python before FastAPI).

### 3. Resource Suggestion
Searches a curated internal library or external APIs (e.g., Coursera, Udemy) for resources matching the skill gap.

## Roadmap Example
```text
Module 1: Cloud Infrastructure (Priority: High)
  - Skill: AWS
  - Resources: [AWS Certified Developer Course]
  - ETA: 3 Weeks

Module 2: Containerization (Priority: Medium)
  - Skill: Docker
  - Resources: [Docker Deep Dive]
  - ETA: 1 Week
```

## Maintenance
The roadmap is updated automatically when a user uploads a new resume version that includes newly acquired skills.
