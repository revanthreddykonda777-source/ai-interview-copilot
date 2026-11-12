import sqlite3
import random

# Connect to the database
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.db import DEFAULT_DB_PATH

conn = sqlite3.connect(DEFAULT_DB_PATH)
cursor = conn.cursor()

# Define topics and their specific keywords/concepts
topics_data = {
    "html": ["HTML5", "Tags", "Attributes", "Forms", "Semantic HTML", "Canvas", "SVG", "Web Storage", "Accessibility (a11y)", "SEO", "Tables", "iframes", "Meta tags", "DOM", "Doctype"],
    "css": ["CSS3", "Flexbox", "Grid", "Animations", "Transitions", "Media Queries", "Selectors", "Specificity", "Box Model", "Positioning", "Variables", "Z-index", "Pseudo-classes", "Pseudo-elements", "Responsive Design"],
    "javascript": ["Closures", "Promises", "Async/Await", "Event Loop", "Hoisting", "Prototypes", "ES6+", "DOM Manipulation", "Fetch API", "Arrow Functions", "Array Methods", "Let/Const/Var", "Scope", "this keyword", "Modules"],
    "sql": ["JOINs", "GROUP BY", "Subqueries", "Indexes", "Normalization", "Transactions", "Triggers", "Views", "Primary Keys", "Foreign Keys", "Aggregate Functions", "ACID properties", "Stored Procedures", "HAVING clause", "UNION"],
    "react": ["Hooks", "Components", "State", "Props", "Context API", "React Router", "Virtual DOM", "useEffect", "useState", "Redux", "Higher-Order Components", "Custom Hooks", "Reconciliation", "Memoization", "Lifecycle Methods"],
    "python": ["Lists", "Dictionaries", "Tuples", "Decorators", "Generators", "List Comprehension", "OOP", "Dunder Methods", "Lambda Functions", "Exception Handling", "File I/O", "Modules", "Pandas", "NumPy", "Flask"],
    "typescript": ["Interfaces", "Types", "Enums", "Generics", "Utility Types", "Decorators", "Modules", "Namespaces", "Type Inference", "Type Assertions", "Union Types", "Intersection Types", "Mapped Types", "Conditional Types", "Strict Mode"],
    "git": ["Commits", "Branches", "Merge", "Rebase", "Cherry-pick", "Stash", "Tags", "Fetch vs Pull", "Resolving Conflicts", "Reset vs Revert", "Reflog", "Hooks", "Submodules", "Worktrees", "Gitflow"],
    "nodejs": ["Event Loop", "Streams", "Buffers", "Express.js", "Middleware", "NPM", "Package.json", "Modules", "File System (fs)", "Path module", "Crypto", "Cluster", "Worker Threads", "Asynchronous I/O", "Error Handling"],
    "dsa": ["Arrays", "Linked Lists", "Stacks", "Queues", "Trees", "Graphs", "Hash Tables", "Binary Search", "Sorting Algorithms", "Dynamic Programming", "Recursion", "Big O Notation", "Heaps", "Tries", "Two Pointers"],
    
    # New Non-Tech Topics
    "hotel_management": ["Front Office", "Housekeeping", "F&B Service", "Revenue Management", "Guest Relations", "Event Planning", "Inventory Management", "Yield Management", "Concierge", "Room Service", "Check-in/Check-out", "Banqueting", "Tourism", "Hospitality Law", "Property Management Systems"],
    "marketing": ["SEO", "Content Marketing", "Social Media", "Email Campaigns", "PPC", "Brand Identity", "Market Research", "Target Audience", "ROI", "Conversion Rate Optimization", "Inbound Marketing", "Affiliate Marketing", "Influencer Marketing", "A/B Testing", "Customer Journey"],
    "hr": ["Recruitment", "Onboarding", "Employee Retention", "Payroll", "Benefits Administration", "Performance Reviews", "Conflict Resolution", "Labor Laws", "Diversity & Inclusion", "Training & Development", "Employee Engagement", "Offboarding", "HRIS", "Compliance", "Workplace Safety"],
    "project_management": ["Agile", "Scrum", "Kanban", "Waterfall", "Risk Management", "Stakeholder Communication", "Resource Allocation", "Gantt Charts", "Sprint Planning", "Scope Creep", "Milestones", "Budgeting", "Quality Assurance", "KPIs", "Post-Mortem"],
    "customer_service": ["Active Listening", "De-escalation", "Ticketing Systems", "Empathy", "Time Management", "Product Knowledge", "Multichannel Support", "Customer Satisfaction (CSAT)", "Net Promoter Score (NPS)", "First Contact Resolution", "Handling Difficult Customers", "CRM Software", "Feedback Loops", "Service Level Agreements (SLA)", "Tone of Voice"]
}

# Templates to generate theoretical questions
question_templates = [
    ("What is {keyword} and why is it important?", "Beginner"),
    ("Explain the concept of {keyword} in simple terms.", "Beginner"),
    ("How do you use {keyword} in a real-world scenario?", "Intermediate"),
    ("What are the best practices when working with {keyword}?", "Intermediate"),
    ("Can you describe a common challenge when dealing with {keyword}?", "Intermediate"),
    ("Compare and contrast {keyword} with its alternatives.", "Advanced"),
    ("How does {keyword} impact performance or efficiency?", "Advanced"),
    ("Explain a complex implementation involving {keyword}.", "Advanced"),
    ("What are the core principles behind {keyword}?", "Beginner"),
    ("How would you troubleshoot an issue related to {keyword}?", "Intermediate")
]

# Templates for coding questions
coding_templates = [
    ("Write a function/code snippet to implement or demonstrate {keyword}.", "Intermediate"),
    ("How do you debug an issue with {keyword}? Show a small code example.", "Intermediate"),
    ("Implement a simple code example utilizing {keyword}.", "Beginner"),
    ("Write the code to optimize {keyword} in a large-scale application.", "Advanced"),
    ("Create a real-world code snippet heavily utilizing {keyword}.", "Advanced")
]

# Templates for SQL query questions
query_templates = [
    ("Write a SQL query demonstrating the use of {keyword}.", "Intermediate"),
    ("How do you optimize a query involving {keyword}? Show an example.", "Advanced"),
    ("Provide a basic SQL example using {keyword}.", "Beginner"),
    ("Write a complex query using {keyword} for a real-world scenario.", "Advanced"),
    ("How would you debug a syntax error in a query containing {keyword}?", "Intermediate")
]

tech_topics = {"html", "css", "javascript", "sql", "react", "python", "typescript", "git", "nodejs", "dsa"}

# Generate and insert questions
total_inserted = 0

for topic_id, keywords in topics_data.items():
    # Only clear this specific topic's rows so resume_<user_id> questions
    # (and any other topic already populated) are never touched.
    cursor.execute("DELETE FROM questions WHERE topic_id = ?", (topic_id,))
    questions_for_topic = []

    for i in range(50):
        keyword = keywords[i % len(keywords)]
        
        # 30% chance for a coding question if it's a tech topic
        if topic_id in tech_topics and random.random() < 0.3:
            if topic_id == "sql":
                template, difficulty = random.choice(query_templates)
            else:
                template, difficulty = random.choice(coding_templates)
            is_coding = True
        else:
            template, difficulty = random.choice(question_templates)
            is_coding = False
            
        q_text = template.format(keyword=keyword)
        
        if is_coding:
            if topic_id == "sql":
                a_text = f"An excellent answer for {keyword} should include a well-structured SQL query. Ensure table names are clear, joins are handled correctly, and the logic directly demonstrates the core concept."
                h_text = f"Think about the SQL syntax required for {keyword}. Start by writing the SELECT or specific clause structure."
            else:
                a_text = f"An excellent answer for {keyword} should include a well-structured code snippet. Ensure variables are named clearly, edge cases are handled, and the logic directly demonstrates the core concept."
                h_text = f"Think about the syntax required for {keyword}. Start by writing the function signature or the outer structure."
        else:
            a_text = f"An excellent answer covering {keyword} should define what it is, explain its primary use cases, and provide an example. Discussing best practices and potential pitfalls also demonstrates deep understanding."
            h_text = f"Think about the core definition of {keyword} and where you have seen it used in projects."
        
        # Add to batch
        q_type = "coding" if is_coding else "theoretical"
        questions_for_topic.append((topic_id, difficulty, q_type, q_text, a_text, h_text))
        total_inserted += 1

    # Insert into database
    cursor.executemany(
        "INSERT INTO questions (topic_id, difficulty, type, question, answer, hint) VALUES (?, ?, ?, ?, ?, ?)",
        questions_for_topic
    )

conn.commit()
conn.close()

from backend.scripts.seed_ai_roles import seed_ai_roles
total_ai = seed_ai_roles()

print(f"Successfully inserted {total_inserted} core + {total_ai} AI role questions into the database!")
