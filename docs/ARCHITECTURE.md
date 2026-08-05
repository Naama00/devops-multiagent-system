DevOps Multi-Agent System
מערכת מרובת-סוכנים (Multi-Agent System) לאוטומציה של משימות DevOps, ניהול תשתית ופעולות Git, המבוססת על LangGraph ו-Model Context Protocol (MCP).

🏗️ ארכיטקטורת המערכת
המערכת משלבת מספר רכיבים מרכזיים ליצירת סביבת עבודה אוטונומית וחכמה:

Orchestrator (LangGraph): מנהל את זרימת העבודה (StateGraph) בין הסוכנים השונים, מקבל את בקשות המשתמש ומנתב אותן לרכיב המתאים.

LLM Engine: שימוש ב-Google Gemini API (gemini-2.0-flash) באמצעות ChatGoogleGenerativeAI.

MCP Integration: חיבור לספק שירותי קוד ותשתית דרך פרוטוקול MCP להרצת פקודות וכלים.

SSL & Network Adaptation: מעקף מותאם לטעינת אישורים בסביבות רשת מסוננות (כדוגמת NetFree) באמצעות Monkey Patching ל-httpx.

🛠️ שירותי הליבה (Services)
המערכת בנויה משלושה שירותים מרכזיים (Microservices):

Git Automation Agent: סוכן המטפל בפעולות ניהול גרסאות, בדיקת סטטוס, יצירת Commits וניהול Branching.

Infrastructure Agent: סוכן האחראי על תפעול ובדיקת תשתיות.

Log & Monitoring Agent: סוכן לניתוח לוגים, זיהוי שגיאות והפקת התראות בזמן אמת.

🚀 התקנה והרצה
1. דרישות קדם
Python 3.10+

מפתח API של Google Gemini

2. הגדרת משתני סביבה
יש ליצור קובץ .env בתיקיית השרש ולהגדיר את מפתח ה-API:

קטע קוד
GOOGLE_API_KEY=your_gemini_api_key_here

3. הרצת המערכת
python -m src.main