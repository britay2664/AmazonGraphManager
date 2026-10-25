# Name: Brian Taylor
# Date: October 25, 2026
# Assignment: 4.5 Performance Assessment -
#             Python Application Accessing a Graph Database
# Purpose: Import Amazon review data and provide an interactive
#          Neo4j menu for creating, reading, updating, and deleting data.

import json
from datetime import datetime
from getpass import getpass
from pathlib import Path

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable


URI = "neo4j://127.0.0.1:7687"

# Only these labels are accepted when building node-creation queries.
NODE_KEYS = {
    "Category": "name",
    "Product": "name",
    "Review": "review_id",
    "Reviewer": "name"
}


def required_input(prompt):
    """Require a nonempty user-entered value."""
    value = input(prompt).strip()
    if not value:
        raise ValueError("The value cannot be blank.")
    return value


def get_stars():
    """Accept a whole-number rating from one to five."""
    value = input("Stars (1-5): ").strip()
    if value not in {"1", "2", "3", "4", "5"}:
        raise ValueError("Stars must be a whole number from 1 to 5.")
    return int(value)


def create_constraints(session):
    # CREATE: Keep identifying properties unique for each node label.
    for label, key in NODE_KEYS.items():
        constraint = f"amazon_{label.lower()}_unique"
        session.run(
            f"CREATE CONSTRAINT {constraint} IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.{key} IS UNIQUE"
        ).consume()


def import_batch(transaction, rows):
    # CREATE: Import nodes and their three required relationship types.
    transaction.run("""
        UNWIND $rows AS row

        MERGE (category:Category {name: row.product_category})
        MERGE (product:Product {name: row.product_id})
        MERGE (reviewer:Reviewer {name: row.reviewer_id})
        MERGE (review:Review {review_id: row.review_id})

        SET review.title = row.review_title,
            review.content = row.review_body,
            review.stars = row.stars

        MERGE (reviewer)-[:WROTE]->(review)
        MERGE (product)-[:CLASSIFIED_AS]->(category)
        MERGE (product)-[:HAS_REVIEW]->(review)
    """, rows=rows).consume()


def import_dataset(session):
    # CREATE: Read the course JSON file and import batches of 250 reviews.
    path = Path(__file__).resolve().parent / "dataset_en_dev.json"

    # Parse and validate the file before writing records.
    rows = []
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue

            record = json.loads(line)
            rows.append({
                "review_id": record["review_id"],
                "product_id": record["product_id"],
                "reviewer_id": record["reviewer_id"],
                "product_category": record["product_category"],
                "review_title": record["review_title"],
                "review_body": record["review_body"],
                "stars": int(record["stars"])
            })

    print(f"Importing {len(rows)} dataset records...")

    for start in range(0, len(rows), 250):
        session.execute_write(import_batch, rows[start:start + 250])

    print("Import complete!")
    show_summary(session)


def show_summary(session):
    # READ: Display counts for all node labels and relationship types.
    print("\nNode counts:")
    for row in session.run("""
        MATCH (n)
        UNWIND labels(n) AS label
        RETURN label, count(*) AS total
        ORDER BY label
    """):
        print(f"{row['label']}: {row['total']}")

    print("\nRelationship counts:")
    for row in session.run("""
        MATCH ()-[r]->()
        RETURN type(r) AS relationship, count(*) AS total
        ORDER BY relationship
    """):
        print(f"{row['relationship']}: {row['total']}")

    total = session.run(
        "MATCH (n) RETURN count(n) AS total"
    ).single()["total"]
    print("Total nodes:", total)


def create_node(session):
    # CREATE: Prompt for a node label and all required properties.
    print("Labels: Category, Product, Review, Reviewer")
    entered = required_input("Node label: ").lower()

    label = next(
        (label for label in NODE_KEYS if label.lower() == entered),
        None
    )
    if label is None:
        raise ValueError("Choose one of the four listed labels.")

    if label == "Review":
        properties = {
            "review_id": required_input("Unique review ID: "),
            "title": required_input("Review title: "),
            "content": required_input("Review content: "),
            "stars": get_stars()
        }
    else:
        properties = {"name": required_input("Node name: ")}

    # The label comes from the fixed allowlist above.
    # Property values are passed as query parameters.
    row = session.run(
        f"CREATE (n:{label}) SET n = $properties "
        "RETURN properties(n) AS node",
        properties=properties
    ).single()
    print("Created:", row["node"])


def create_relationship(session):
    # CREATE: Connect existing Product nodes to Category or Review nodes.
    print("1. Product -> Category (CLASSIFIED_AS)")
    print("2. Product -> Review (HAS_REVIEW)")
    choice = input("Relationship option: ").strip()

    product = required_input("Product name (product_id): ")

    if choice == "1":
        target = required_input("Category name: ")
        query = """
            MATCH (p:Product {name: $product})
            MATCH (c:Category {name: $target})
            MERGE (p)-[r:CLASSIFIED_AS]->(c)
            RETURN type(r) AS relationship
        """
    elif choice == "2":
        target = required_input("Review ID: ")
        query = """
            MATCH (p:Product {name: $product})
            MATCH (review:Review {review_id: $target})
            MERGE (p)-[r:HAS_REVIEW]->(review)
            RETURN type(r) AS relationship
        """
    else:
        raise ValueError("Select 1 or 2.")

    result = session.run(
        query, product=product, target=target
    ).single()

    if result is None:
        print("No relationship created. Check that both nodes exist.")
    else:
        print("Relationship is present:", result["relationship"])


def count_category_products(session):
    # READ: Count distinct Product nodes related to a supplied category.
    name = required_input("Category name: ")
    row = session.run("""
        MATCH (p:Product)-[:CLASSIFIED_AS]->(c:Category {name: $name})
        RETURN count(DISTINCT p) AS total
    """, name=name).single()
    print(f"Products related to '{name}': {row['total']}")


def count_reviewer_reviews(session):
    # READ: Count distinct Review nodes written by a supplied reviewer.
    name = required_input("Reviewer name (reviewer_id): ")
    row = session.run("""
        MATCH (:Reviewer {name: $name})-[:WROTE]->(review:Review)
        RETURN count(DISTINCT review) AS total
    """, name=name).single()
    print(f"Reviews related to '{name}': {row['total']}")


def update_review(session):
    # UPDATE: Change one review's title, content, or star rating.
    review_id = required_input("Review ID to update: ")

    existing = session.run("""
        MATCH (review:Review {review_id: $review_id})
        RETURN properties(review) AS review
    """, review_id=review_id).single()

    if existing is None:
        print("Review not found.")
        return

    print("Current review:", existing["review"])
    field = required_input("Field (title, content, stars): ").lower()

    if field not in {"title", "content", "stars"}:
        raise ValueError("Choose title, content, or stars.")

    value = get_stars() if field == "stars" else required_input("New value: ")

    row = session.run("""
        MATCH (review:Review {review_id: $review_id})
        SET review += $changes
        RETURN properties(review) AS review
    """, review_id=review_id, changes={field: value}).single()
    print("Updated review:", row["review"])


def delete_category(session):
    # DELETE: Remove a named category and its attached relationships.
    name = required_input("Category name to delete: ")

    if input(f"Delete category '{name}'? Type YES: ").strip() != "YES":
        print("Deletion cancelled.")
        return

    summary = session.run("""
        MATCH (c:Category {name: $name})
        DETACH DELETE c
    """, name=name).consume()

    print("Category nodes deleted:", summary.counters.nodes_deleted)
    print("Relationships deleted:", summary.counters.relationships_deleted)


def delete_relationships(session):
    # DELETE: Remove every relationship in the selected lab database.
    if input("Delete ALL relationships? Type YES: ").strip() != "YES":
        print("Deletion cancelled.")
        return

    summary = session.run(
        "MATCH ()-[r]->() DELETE r"
    ).consume()
    print("Relationships deleted:", summary.counters.relationships_deleted)


def delete_nodes(session):
    # DELETE: Remove every node after relationships have been removed.
    if input("Delete ALL nodes? Type YES: ").strip() != "YES":
        print("Deletion cancelled.")
        return

    relationships = session.run(
        "MATCH ()-[r]->() RETURN count(r) AS total"
    ).single()["total"]

    if relationships:
        print("Remove all relationships with option 8 first.")
        return

    summary = session.run("MATCH (n) DELETE n").consume()
    print("Nodes deleted:", summary.counters.nodes_deleted)

    remaining = session.run(
        "MATCH (n) RETURN count(n) AS total"
    ).single()["total"]
    print("Remaining nodes:", remaining)


def menu():
    print("\nSystem date and time:",
          datetime.now().astimezone().isoformat(timespec="seconds"))
    print("\nAMAZON GRAPH MANAGER")
    print("1. Import JSON dataset")
    print("2. Create a node")
    print("3. Create a relationship")
    print("4. Count products by category")
    print("5. Count reviews by reviewer")
    print("6. Update a review")
    print("7. Delete a category")
    print("8. Delete all relationships")
    print("9. Delete all nodes")
    print("10. Display graph counts")
    print("0. Exit")


def main():
    # CONNECT: Prompt for the password rather than saving it in the code.
    print("Use the credentials for the Amazon Project instance.")
    password = getpass("Neo4j password: ")

    try:
        with GraphDatabase.driver(
            URI, auth=("neo4j", password)
        ) as driver:
            driver.verify_connectivity()
            print("Connected to local Neo4j.")

            with driver.session(database="neo4j") as session:
                create_constraints(session)

                # MENU: Accept operations until the user chooses Exit.
                while True:
                    menu()
                    choice = input("Select an option: ").strip()

                    try:
                        if choice == "1":
                            import_dataset(session)
                        elif choice == "2":
                            create_node(session)
                        elif choice == "3":
                            create_relationship(session)
                        elif choice == "4":
                            count_category_products(session)
                        elif choice == "5":
                            count_reviewer_reviews(session)
                        elif choice == "6":
                            update_review(session)
                        elif choice == "7":
                            delete_category(session)
                        elif choice == "8":
                            delete_relationships(session)
                        elif choice == "9":
                            delete_nodes(session)
                        elif choice == "10":
                            show_summary(session)
                        elif choice == "0":
                            print("Program has ended!")
                            break
                        else:
                            print("Choose a listed option.")
                    except (Neo4jError, ServiceUnavailable,
                            ValueError, OSError, KeyError) as error:
                        print("Operation failed:", error)

    except (Neo4jError, ServiceUnavailable) as error:
        print("Database connection or setup failed:", error)


if __name__ == "__main__":
    main()