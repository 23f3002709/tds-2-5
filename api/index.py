from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mangum import Mangum
import json
import statistics
from typing import List, Dict

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Load telemetry data
def load_telemetry():
    try:
        with open('q-vercel-latency.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading telemetry: {e}")
        return {}

TELEMETRY_DATA = load_telemetry()

# Request model
class LatencyRequest(BaseModel):
    regions: List[str]
    threshold_ms: int = 180

def calculate_percentile(values, percentile):
    """Calculate the nth percentile of a list of values"""
    if not values:
        return 0
    sorted_values = sorted(values)
    index = (percentile / 100) * (len(sorted_values) - 1)
    lower = int(index)
    upper = lower + 1
    weight = index - lower
    
    if upper >= len(sorted_values):
        return sorted_values[-1]
    
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight

def analyze_region(region_data, threshold_ms) -> Dict:
    """Analyze latency data for a single region"""
    if not region_data:
        return {
            "avg_latency": 0,
            "p95_latency": 0,
            "avg_uptime": 0,
            "breaches": 0
        }
    
    latencies = [record["latency_ms"] for record in region_data]
    uptimes = [record["uptime"] for record in region_data]
    
    return {
        "avg_latency": round(statistics.mean(latencies), 2),
        "p95_latency": round(calculate_percentile(latencies, 95), 2),
        "avg_uptime": round(statistics.mean(uptimes), 4),
        "breaches": sum(1 for lat in latencies if lat > threshold_ms)
    }

@app.post("/api")
async def analyze_latency(request: LatencyRequest):
    """Analyze latency metrics for specified regions"""
    response = {}
    
    for region in request.regions:
        if region in TELEMETRY_DATA:
            response[region] = analyze_region(TELEMETRY_DATA[region], request.threshold_ms)
        else:
            response[region] = {
                "avg_latency": 0,
                "p95_latency": 0,
                "avg_uptime": 0,
                "breaches": 0
            }
    
    return response

# Vercel serverless handler
handler = Mangum(app)
