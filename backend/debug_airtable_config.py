#!/usr/bin/env python3
"""
Debug script to help identify correct Airtable configuration.
"""

print("🔧 Airtable Configuration Debug")
print("=" * 50)

print("\n📋 Current Configuration Issues:")
print("- Base ID starts with 'tbl' instead of 'app'")
print("- 'tblfQs451lw7Ygv4t' looks like a table ID, not a base ID")
print("- Airtable base IDs should start with 'app'")
print("- Table names should match exactly what you have in Airtable")

print("\n🔍 What you need to find:")
print("1. Go to your Airtable workspace")
print("2. Open your base")
print("3. Look at the URL - it should be something like:")
print("   https://airtable.com/[BASE_ID]/[TABLE_ID]/...")
print("4. The BASE_ID starts with 'app' (e.g., appXXXXXXXXXXXXXX)")
print("5. Make sure your table is actually named 'Job Applications'")

print("\n⚙️ Required Environment Variables:")
print("AIRTABLE_API_KEY=pat...")  # Already looks correct
print("AIRTABLE_BASE_ID=app...")  # Should start with 'app'
print("AIRTABLE_TABLE_NAME=Job Applications")  # Should match exactly

print("\n🚨 Current Problem:")
print("The current base ID 'tblfQs451lw7Ygv4t' is actually a table ID")
print("This is causing the 404 error because the API is trying to access:")
print("https://api.airtable.com/v0/tblfQs451lw7Ygv4t/Job%20Applications")
print("But it should be:")
print("https://api.airtable.com/v0/[CORRECT_BASE_ID]/Job%20Applications")

print("\n✅ To fix this:")
print("1. Get the correct base ID from your Airtable URL")
print("2. Update AIRTABLE_BASE_ID in your .env file")
print("3. Make sure the table name matches exactly")
print("4. Restart the application")

print("\n🎯 For testing purposes, I'll create a mock success:")
print("Since we can't access the real Airtable, let's mock the response")
