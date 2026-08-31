# testAllEndpoints.ps1
# PS94 - Mental Health Monitoring backend ke saare endpoints test karne ke liye
# Run: powershell me is file ko chalao: .\testAllEndpoints.ps1
# (server pehle se node server.js se running hona chahiye)

$baseUrl = "http://127.0.0.1:3000"

Write-Host "`n== 1. TEST API ==" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$baseUrl/test" -Method GET

Write-Host "`n== 2. REGISTER VICTIM V-1001 ==" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$baseUrl/victim" -Method POST -ContentType "application/json" -Body '{
  "victimId": "V-1001",
  "name": "Test Victim One",
  "contact": "9999999999",
  "caseType": "witness_intimidation",
  "district": "Prayagraj",
  "state": "Uttar Pradesh"
}'

Write-Host "`n== 3. GET VICTIM PROFILE ==" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$baseUrl/victim/V-1001" -Method GET

Write-Host "`n== 4. SEND DISTRESS SCORES (rising trend: 45 -> 60 -> 75 -> 85) ==" -ForegroundColor Cyan

Write-Host "`n-- Score 45 --"
Invoke-RestMethod -Uri "$baseUrl/distress-score" -Method POST -ContentType "application/json" -Body '{"victimId":"V-1001","score":45,"contributingFactors":["mild anxiety detected"]}'

Write-Host "`n-- Score 60 --"
Invoke-RestMethod -Uri "$baseUrl/distress-score" -Method POST -ContentType "application/json" -Body '{"victimId":"V-1001","score":60,"contributingFactors":["reduced engagement"]}'

Write-Host "`n-- Score 75 --"
Invoke-RestMethod -Uri "$baseUrl/distress-score" -Method POST -ContentType "application/json" -Body '{"victimId":"V-1001","score":75,"contributingFactors":["negative sentiment in last 3 messages"]}'

Write-Host "`n-- Score 85 (should trigger RED alert) --"
Invoke-RestMethod -Uri "$baseUrl/distress-score" -Method POST -ContentType "application/json" -Body '{"victimId":"V-1001","score":85,"contributingFactors":["expressed hopelessness","no response to last 2 check-ins"]}'

Write-Host "`n== 5. GET FULL SCORE HISTORY ==" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$baseUrl/distress-score/V-1001" -Method GET

Write-Host "`n== 6. GET TOP PRIORITY CASES ==" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$baseUrl/priority-cases?n=5" -Method GET

Write-Host "`n== 7. GET ALL OPEN ALERTS ==" -ForegroundColor Cyan
Invoke-RestMethod -Uri "$baseUrl/alerts?status=open" -Method GET

Write-Host "`n== 8. RESOLVE AN ALERT (replace ALERT_ID_HERE with actual _id from step 7) ==" -ForegroundColor Yellow
Write-Host 'Invoke-RestMethod -Uri "$baseUrl/alerts/ALERT_ID_HERE" -Method PATCH -ContentType "application/json" -Body ''{"status":"resolved"}'''

Write-Host "`n== DONE - sab endpoints test ho gaye ==" -ForegroundColor Green

# ---- Agar poora JSON detail dekhna ho (nested fields properly dikhega) ----
Write-Host "`n== FULL DETAIL VIEW (score history + priority cases + alerts) ==" -ForegroundColor Magenta

Write-Host "`n-- Score History --"
Invoke-RestMethod -Uri "$baseUrl/distress-score/V-1001" -Method GET | ConvertTo-Json -Depth 5

Write-Host "`n-- Priority Cases --"
Invoke-RestMethod -Uri "$baseUrl/priority-cases?n=5" -Method GET | ConvertTo-Json -Depth 5

Write-Host "`n-- Open Alerts --"
Invoke-RestMethod -Uri "$baseUrl/alerts?status=open" -Method GET | ConvertTo-Json -Depth 5