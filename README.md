# Amazon Graph Manager

Author: Brian Taylor

## Program

amazonGraphManager.py is an interactive Python application for
managing Amazon review data in a local Neo4j graph database.

Assignment: 4.5 Performance Assessment -
Python Application Accessing a Graph Database.

The application supports:
- Importing Category, Product, Review, and Reviewer nodes
- Creating WROTE, CLASSIFIED_AS, and HAS_REVIEW relationships
- Creating individual nodes and product relationships
- Counting products by category and reviews by reviewer
- Updating review properties
- Deleting categories, all relationships, and all nodes

## Requirements

- Python 3.10 or later
- Neo4j Desktop with a running Amazon Project instance
- The course dataset_en_dev.json file

## Setup

Place dataset_en_dev.json beside amazonGraphManager.py.
Download the dataset separately from Canvas.

In Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\amazonGraphManager.py
```

The application connects to neo4j://127.0.0.1:7687 and uses
the neo4j database. It prompts for the database password at startup.

Select option 1 to import the dataset before testing other operations.
Deletion options require confirmation. Options 8 and 9 remove all
relationships and nodes from the connected database.

The dataset and virtual environment are excluded from GitHub.