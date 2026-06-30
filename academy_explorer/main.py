from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from dotenv import load_dotenv
from mock_data import mock_academies
import urllib.parse
from bs4 import BeautifulSoup # To strip html tags from Naver API response if needed
import re

load_dotenv()

app = FastAPI(title="Academy Explorer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# Naver API URLs
LOCAL_API_URL = "https://openapi.naver.com/v1/search/local.json"
BLOG_API_URL = "https://openapi.naver.com/v1/search/blog.json"

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

@app.get("/api/academies")
async def get_academies(category: str = "all", query: str = "", region: str = "시흥 은행동"):
    # If API keys are not set, return mock data
    if not NAVER_CLIENT_ID or NAVER_CLIENT_ID == "your_client_id_here":
        return JSONResponse(content={"status": "mock", "data": mock_academies})
    
    # Otherwise, fetch from Naver Local API
    # We construct a search query.
    search_query = f"{region} "
    if query:
        search_query += query
    elif category != "all" and category != "favorites":
        search_query += category + " 학원"
    else:
        search_query += "학원"
        
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    params = {
        "query": search_query,
        "display": 15,
        "start": 1,
        "sort": "random" # sort by relevance
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(LOCAL_API_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            items = data.get("items", [])
            academies = []
            
            for idx, item in enumerate(items):
                # Clean html tags from title
                title = clean_html(item.get("title", ""))
                
                # Fetch reviews for this academy
                reviews = []
                review_params = {
                    "query": f"{region} {title} 후기",
                    "display": 3
                }
                review_res = await client.get(BLOG_API_URL, headers=headers, params=review_params)
                if review_res.status_code == 200:
                    r_data = review_res.json()
                    for r_item in r_data.get("items", []):
                        reviews.append({
                            "author": r_item.get("bloggername"),
                            "date": r_item.get("postdate"),
                            "content": clean_html(r_item.get("description")),
                            "rating": 5, # Naver blog api doesn't give ratings, defaulting to 5
                            "link": r_item.get("link")
                        })

                encoded_address = urllib.parse.quote(item.get("roadAddress") or item.get("address"))
                mapUrl = f"https://map.naver.com/v5/search/{encoded_address}"
                
                # Fallback image based on category
                img = "https://images.unsplash.com/photo-1577896851231-70ef18881754?auto=format&fit=crop&w=600&q=80"
                if "수영" in title or category == "수영":
                    img = "https://images.unsplash.com/photo-1519315901367-f34ff9154487?auto=format&fit=crop&w=600&q=80"
                elif "축구" in title or category == "축구":
                    img = "https://images.unsplash.com/photo-1518605368461-1ee7c683ee86?auto=format&fit=crop&w=600&q=80"
                elif "코딩" in title or category == "코딩":
                    img = "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=600&q=80"
                elif "수학" in title or category == "수학":
                    img = "https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=600&q=80"

                academies.append({
                    "id": idx + 1,
                    "name": title,
                    "category": category if category != "all" else "학원",
                    "address": item.get("roadAddress") or item.get("address"),
                    "phone": item.get("telephone") or "연락처 정보 없음",
                    "rating": 5.0, # Default since API doesn't provide rating
                    "reviewCount": len(reviews),
                    "image": img,
                    "description": clean_html(item.get("description", "")) or f"{title}에 대한 상세 정보입니다.",
                    "programs": [
                        { "name": "기본 수강반", "duration": "상시", "time": "전화 문의", "price": "상담 필요" }
                    ],
                    "reviews": reviews,
                    "mapUrl": mapUrl
                })
            
            return JSONResponse(content={"status": "api", "data": academies})
            
        except Exception as e:
            # On any error, fallback to mock data
            print(f"Error fetching from Naver API: {e}")
            return JSONResponse(content={"status": "mock", "data": mock_academies})

# Mount static files (HTML/CSS/JS) at root
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
