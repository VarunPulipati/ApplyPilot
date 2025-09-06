# tests/smoke.ps1 — single end-to-end application (preview + submit)

$base = "http://127.0.0.1:8000"

# 0) Ensure API is running in another terminal:
#    .\.venv\Scripts\Activate.ps1
#    $env:GEMINI_API_KEY = "<YOUR_KEY>"
#    uvicorn app.main:app --reload

# 1) Get or create profile
$profiles = Invoke-RestMethod -Uri "$base/profiles" -Method GET
if (-not $profiles) {
  $profileBody = @{
    name="Varun Pulipati";
    email="varunpulipati26@gmail.com";
    phone="+1-573-810-1866";
    location="Atlanta, GA";
    skills_csv="Python, SQL, PySpark, Databricks, Airflow, Azure, AWS, Power BI, TensorFlow, scikit-learn, NLP, MLOps, Snowflake, Data Warehousing, ETL/ELT";
    resume_path=""
  } | ConvertTo-Json
  $created = Invoke-RestMethod -Uri "$base/profiles" -Method POST -ContentType "application/json" -Body $profileBody
  $profileId = $created.id
} else {
  $profileId = $profiles[0].id
}

# 2) Upload your static PDF resume (recommended)
#    Change this path if your file lives elsewhere (you can also use the copy in your repo).
# 2) Upload your static PDF resume (recommended)
$resumeFile = "C:\Users\varun\Desktop\Varun_Pulipati_Resume.pdf"
$uploadUri  = "$base/profiles/$profileId/resume"

if (Test-Path $resumeFile) {
  try {
    if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
      # Prefer curl.exe if available
      $raw = & curl.exe -s -S -F ("file=@{0};type=application/pdf" -f $resumeFile) $uploadUri
      $upload = $raw | ConvertFrom-Json
    } else {
      # PS 5.1 fallback using .NET HttpClient (multipart/form-data)
      Add-Type -AssemblyName System.Net.Http
      $client = [System.Net.Http.HttpClient]::new()
      $mp     = [System.Net.Http.MultipartFormDataContent]::new()
      $fs     = [System.IO.File]::OpenRead($resumeFile)
      $fc     = [System.Net.Http.StreamContent]::new($fs)
      $fc.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse("application/pdf")
      $mp.Add($fc, "file", [System.IO.Path]::GetFileName($resumeFile))
      $resp   = $client.PostAsync($uploadUri, $mp).Result
      $raw    = $resp.Content.ReadAsStringAsync().Result
      $fs.Dispose(); $client.Dispose()
      $upload = $raw | ConvertFrom-Json
    }

    if (-not $upload.ok) { throw "Upload failed. Response: $($upload | ConvertTo-Json -Depth 4)" }
    "Uploaded resume → $($upload.resume_path)"
  }
  catch {
    Write-Host "ERROR uploading resume: $($_.Exception.Message)"
    throw
  }
} else {
  Write-Host "WARNING: Resume not found at $resumeFile. Using AI resume instead."
}

# 3) Import one Greenhouse board (change slug if you prefer)
$importBody = @{ source="greenhouse"; company="datadog" } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/sources/import-company" -Method POST -ContentType "application/json" -Body $importBody | Out-Host

# 4) Pick a job
$jobs = Invoke-RestMethod -Uri "$base/jobs" -Method GET
if (-not $jobs) { throw "No jobs found. Try a different company slug." }
$jobId = $jobs[0].id

# 5) Preview (safe)
$previewBody = @{ job_id=$jobId; profile_id=$profileId; simulate=$true; resume_mode="static" } | ConvertTo-Json
$preview = Invoke-RestMethod -Uri "$base/apply" -Method POST -ContentType "application/json" -Body $previewBody
"Resume used: $($preview.resume_pdf)"
"Questions found: $($preview.found_questions.Count)"

# 6) Submit (real)
$submitBody = @{ job_id=$jobId; profile_id=$profileId; simulate=$false; resume_mode="static" } | ConvertTo-Json
$submit = Invoke-RestMethod -Uri "$base/apply" -Method POST -ContentType "application/json" -Body $submitBody
"Submit OK: $($submit.ok)  Confirmation: $($submit.confirmation)"
"Applications log: $($submit.excel)"
