@echo off
setlocal
cd /d %~dp0
set PY=py -3.14

schtasks /Create /F /TN "PolyBot_KPI_5min" /SC MINUTE /MO 5 /TR "%PY% %~dp0kpi_snapshot.py" >nul
schtasks /Create /F /TN "PolyBot_Watchdog_1min" /SC MINUTE /MO 1 /TR "%PY% %~dp0stale_watchdog.py" >nul
schtasks /Create /F /TN "PolyBot_DailyReport_2359" /SC DAILY /ST 23:59 /TR "%PY% %~dp0daily_validation_report.py" >nul
schtasks /Create /F /TN "PolyBot_Summary_AM" /SC DAILY /ST 08:00 /TR "%PY% %~dp0send_summary.py" >nul
schtasks /Create /F /TN "PolyBot_Summary_PM" /SC DAILY /ST 20:00 /TR "%PY% %~dp0send_summary.py" >nul

echo Scheduled tasks installed.
echo Use Task Scheduler GUI to verify user/run permissions.
