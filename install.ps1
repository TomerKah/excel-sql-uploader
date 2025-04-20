Write-Host "🔍 Checking for Python installation..."

$python = Get-Command python -ErrorAction SilentlyContinue

if (-not $python) {
    Write-Host "❌ Python is not installed. Please install Python 3.8 or later from https://www.python.org/downloads/"
    Pause
    exit
}

Write-Host "`n📦 Installing required Python packages..."
pip install -r requirements.txt

Write-Host "`n🚀 Launching the app..."
Start-Process powershell -ArgumentList "streamlit run app.py"

Write-Host "`n✅ Done! Streamlit will open the app in your browser."
Pause
