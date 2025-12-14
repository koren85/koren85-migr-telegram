#!/usr/bin/env python3
"""
Simple script to test notification system by simulating database changes
"""
import asyncio
# import requests  # Not available, using curl instead
import time

async def test_notifications():
    """Test notification system"""
    print("🧪 Тестирование системы уведомлений...")
    
    # Simulate database change by calling the notification engine directly
    base_url = "http://localhost:8090"
    
    # Check if server is running
    try:
        response = requests.get(f"{base_url}/api/stats")
        print(f"✅ Сервер доступен: {response.json()}")
    except Exception as e:
        print(f"❌ Сервер недоступен: {e}")
        return
    
    # Get current rules
    try:
        response = requests.get(f"{base_url}/api/rules?active_only=true")
        rules = response.json()
        print(f"📋 Активных правил: {len(rules)}")
        for rule in rules:
            print(f"  - {rule['name']} ({rule['condition_type']})")
    except Exception as e:
        print(f"❌ Ошибка получения правил: {e}")
        return
    
    # Try to simulate notification manually
    print("\n🔄 Симуляция уведомления...")
    
    # We'll simulate this by making API calls to trigger conditions
    test_values = [
        ("processing", "completed"),
        ("completed", "processing"), 
        ("processing", "failed"),
        ("failed", "processing")
    ]
    
    for i, (old_val, new_val) in enumerate(test_values):
        print(f"\n📤 Тест {i+1}: {old_val} → {new_val}")
        
        # We would need to call notification engine directly
        # For now, let's just wait and see if any real changes trigger
        await asyncio.sleep(2)
    
    print("\n✅ Тестирование завершено")
    print("📞 Используйте команду /test_rules в Telegram боте для принудительного тестирования")

if __name__ == "__main__":
    asyncio.run(test_notifications())