from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated, Any
from dotenv import load_dotenv
import logging
import os
import time
# from motor.motor_asyncio import AsyncIOMotorClient
# from datetime import datetime
# from urllib.parse import quote_plus
# import asyncio

from cseTokenFetcher import get_cse_tok
from telegramNew import Telegram

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# FastAPI CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints
@app.get('/api/v1')
async def root():
    return {"message": "Congrats! API is working"}


@app.get("/api/v1/telegram/dashboard")
async def telegram_board(phrase1: Annotated[str, Query(min_length=3)]):
    phrase1 = phrase1.lower()
    NOMIC_API_KEY = os.environ["NOMIC_API_KEY"] or "NOMIC_API_KEY"

    # Check for cached data
    # cached = await get_cached_insights("telegram", phrase1)
    # if cached:
    #     return cached["insights"]
    strt = time.time()
    gOOGLE_CSE_API_KEY = await get_cse_tok()
    end = time.time()

    print("\n Processing time: ", end-strt)
    # Compute new insights
    strt1 = time.time()
    telegram = Telegram(phrase1, gOOGLE_CSE_API_KEY, NOMIC_API_KEY)
    await telegram.get_data()
    insights = telegram.generate_insights()
    end1 = time.time()
    print("\n Processing time2: ", end1-strt1)

    # Cache the results
    # await cache_insights("telegram", phrase1, insights)
    return insights
