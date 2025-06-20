#!/usr/bin/env python3
import requests
import json

def check_sites():
    """登録されているサイト一覧を確認"""
    url = "http://54.64.110.132:8000/api/sites/"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            sites = response.json()
            print("=== 登録サイト一覧 ===")
            for site in sites:
                print(f"ID: {site['id']}, Name: {site['name']}, URL: {site['url']}, Active: {site['active']}")
            
            if not sites:
                print("❌ サイトが登録されていません。")
            else:
                print(f"\n✅ {len(sites)}件のサイトが見つかりました。")
                print("\n正しいsite_urlを使用してください:")
                for site in sites:
                    if site['url']:
                        print(f"  site_url={site['url']}")
        else:
            print(f"❌ API error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def create_test_site():
    """テスト用サイトを作成"""
    url = "http://54.64.110.132:8000/api/sites/"
    data = {
        "name": "CheerjobTest",
        "url": "cheerjob"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code in [200, 201]:
            print("✅ テストサイトを作成しました")
        else:
            print("❌ サイト作成に失敗しました")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("1. サイト一覧確認")
    check_sites()
    
    print("\n" + "="*50)
    print("2. テストサイト作成")
    create_test_site()
    
    print("\n" + "="*50)
    print("3. 再度サイト一覧確認")
    check_sites() 