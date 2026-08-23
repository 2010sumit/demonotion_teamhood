# KNIGHTHOOD Engine - Important Run Note

## 1. Create the environment file

Project root folder me `.env` naam ki file banayein. Ye file `api` folder ke andar nahi, isi folder me honi chahiye jahan `config.py` aur `index.html` hain.

Required variables:

```env
GEMINI_API_KEY=your_gemini_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id
```

Optional variable:

```env
GROQ_API_KEY=your_groq_api_key
GOOGLE_PROJECT_ID=your_google_project_id
```

`GROQ_API_KEY` optional hai. Gemini aur OpenRouter me se kam se kam ek AI key honi chahiye. Actual values apni API keys se replace karein. Quotes ki zaroorat nahi hai.

## 2. Notion setup

1. Notion me ek integration banayein aur uska token `NOTION_TOKEN` me dalein.
2. Target Notion database open karein.
3. Database ko integration ke saath share karein.
4. Database ID ko `NOTION_DATABASE_ID` me dalein.
5. Database me ye properties honi chahiye:
   - `Topic Name` - Title
   - `Status` - Select, for example `Review Pending`
   - `Timestamp` - Rich text

## 3. Install dependencies

PowerShell me project folder open karke run karein:

```powershell
python -m pip install -r requirements.txt
```

## 4. Start the local server

Project root folder se run karein:

```powershell
python api/index.py
```

Server start hone ke baad browser me ye URL open karein:

```text
http://127.0.0.1:5000
```

`index.html` ko directly double-click karke open na karein. Hamesha local server URL use karein.

## 5. Check environment variables

Browser me ye URL open karein:

```text
http://127.0.0.1:5000/api/config-status
```

Expected response me ye values `true` honi chahiye:

```json
{
  "gemini": true,
  "openrouter": true,
  "notion_token": true,
  "notion_db": true,
  "success": true
}
```

`groq` false hona allowed hai, kyunki Groq optional hai.

## 6. Demo steps for judges

1. `http://127.0.0.1:5000` open karein.
2. Video URL tab me valid YouTube URL paste karein.
3. `Process & Annotate to Notion` button click karein.
4. System audio transcript aur video keyframes analyze karega.
5. Generated markdown output page par show hoga.
6. Successful Notion sync ke baad `Open Notion Page` link show hoga.
7. Link open karke Notion database entry verify karein.

## 7. Important limits

- Vercel direct file upload limit approximately 4.5 MB hai.
- Large media ke liye YouTube URL use karein.
- Local server par uploaded audio/video files use ki ja sakti hain.
- AI provider quota khatam hone par generated output fail ya fallback ho sakta hai.
- API keys ko GitHub, screenshots, ya public files me share na karein.

## 8. Stop the server

PowerShell window me `Ctrl + C` press karein.

## 9. Troubleshooting

### `Unexpected token` ya JSON error

Page ko refresh karein aur latest deployment/local server use karein. Browser developer console me actual server response check karein.

### Config status me `false`

Variable name exact spelling se check karein, `.env` project root me rakhein, phir server restart karein.

### Notion page create nahi hoti

`NOTION_TOKEN` verify karein, database ko integration ke saath share karein, aur `NOTION_DATABASE_ID` check karein.

### Output bahut der tak load hota hai

Short YouTube video use karein. Vercel par serverless execution time limited hota hai; production deployment me environment variables ke liye Preview aur Production dono select karein.
