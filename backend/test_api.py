#!/usr/bin/env python3
import requests
import json

# APIテスト用スクリプト
def test_convert_api():
    url = "http://localhost:8000/api/convert/"
    
    # テストファイルのパス
    file_path = "/app/test_data/test.docx"
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'site_url': 'cheerjob'}
            
            response = requests.post(url, files=files, data=data)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("✅ API test successful!")
            else:
                print("❌ API test failed!")
                
    except FileNotFoundError:
        print(f"❌ Test file not found: {file_path}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_convert_api() 