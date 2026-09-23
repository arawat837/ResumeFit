"""
Job Description presets for popular student roles:
1. Data Analyst
2. Consultant
3. Marketing Specialist
4. Human Resources (HR) Generalist
"""

ROLE_PRESETS = {
    "data_analyst": {
        "id": "data_analyst",
        "title": "Data Analyst",
        "description": (
            "We are seeking an entry-level Data Analyst to transform complex datasets into actionable business insights. "
            "Responsibilities include writing SQL queries, building dashboards in Tableau or PowerBI, conducting statistical analysis, "
            "cleaning and validating datasets using Python or R, and collaborating with cross-functional teams to identify key performance metrics. "
            "Requirements: Proficiency in SQL, Python (pandas, numpy), data visualization (Tableau, PowerBI), Excel modeling, "
            "and strong communication skills to present analytical findings to non-technical stakeholders."
        ),
        "required_skills": ["SQL", "Python", "Tableau", "PowerBI", "Excel", "Data Analysis", "Statistics"],
        "keywords": ["ETL", "dashboards", "data cleaning", "metrics", "pandas", "data modeling", "reporting"]
    },
    "consultant": {
        "id": "consultant",
        "title": "Management / Strategy Consultant",
        "description": (
            "Seeking an Associate / Junior Consultant to support strategic client engagements and business transformation initiatives. "
            "Responsibilities include structured problem solving, financial and qualitative modeling, competitor benchmarking, "
            "conducting executive stakeholder interviews, and drafting persuasive presentation decks for client leadership. "
            "Requirements: Strong analytical and quantitative skills, proficiency in Excel financial modeling and PowerPoint slide design, "
            "demonstrated leadership, structured thinking frameworks, and exceptional written and verbal communication."
        ),
        "required_skills": ["Financial Modeling", "Excel", "PowerPoint", "Problem Solving", "Stakeholder Management", "Strategy"],
        "keywords": ["benchmarking", "market research", "client presentations", "frameworks", "qualitative analysis", "deliverables"]
    },
    "marketing": {
        "id": "marketing",
        "title": "Marketing Specialist",
        "description": (
            "Looking for a growth-oriented Marketing Specialist to manage digital campaigns and brand positioning. "
            "Responsibilities include executing content marketing strategies, running paid social and search (SEO/SEM) campaigns, "
            "monitoring conversion funnels with Google Analytics, conducting A/B copy testing, and reporting on marketing ROI. "
            "Requirements: Experience with Google Analytics, SEO/SEM fundamentals, social media marketing, email campaign tools (e.g. Mailchimp, HubSpot), "
            "content creation, copywriting, and data-driven optimization."
        ),
        "required_skills": ["Google Analytics", "SEO", "SEM", "Content Strategy", "Social Media Marketing", "Copywriting", "A/B Testing"],
        "keywords": ["conversion rate", "campaigns", "funnel optimization", "digital marketing", "HubSpot", "ROI", "branding"]
    },
    "hr": {
        "id": "hr",
        "title": "Human Resources (HR) Generalist",
        "description": (
            "Seeking an entry-level HR Generalist / Coordinator to support people operations and talent acquisition. "
            "Responsibilities include screening candidate resumes, coordinating full-cycle interview schedules, managing employee onboarding, "
            "maintaining records in HR Information Systems (HRIS like Workday or BambooHR), supporting compliance, and organizing employee engagement events. "
            "Requirements: Strong interpersonal and communication skills, discretion with confidential employee data, "
            "familiarity with HRIS tools, talent recruitment basics, and organizational skills."
        ),
        "required_skills": ["Talent Acquisition", "Onboarding", "HRIS", "Employee Relations", "Communication", "Compliance"],
        "keywords": ["recruitment", "Workday", "BambooHR", "interview coordination", "performance management", "benefits"]
    }
}
