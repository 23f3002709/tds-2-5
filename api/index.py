import json
import statistics
import os

# Load telemetry data from file
def load_telemetry():
    try:
        # Try multiple possible paths for Vercel deployment
        possible_paths = [
            'q-vercel-latency.json',
            '../q-vercel-latency.json',
            '/var/task/q-vercel-latency.json',
            os.path.join(os.path.dirname(__file__), '../q-vercel-latency.json'),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading telemetry: {e}")
        return {}

TELEMETRY_DATA = load_telemetry()

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

def analyze_region(region_data, threshold_ms):
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

def handler(event, context):
    """Main handler function for Vercel serverless"""
    
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS' or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            },
            'body': ''
        }
    
    # Only handle POST requests
    method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method')
    if method != 'POST':
        return {
            'statusCode': 405,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            },
            'body': json.dumps({'error': 'Method not allowed'})
        }
    
    try:
        # Parse request body
        body = event.get('body', '{}')
        if isinstance(body, str):
            request_data = json.loads(body)
        else:
            request_data = body
        
        regions = request_data.get('regions', [])
        threshold_ms = request_data.get('threshold_ms', 180)
        
        # Calculate metrics for each region
        response = {}
        for region in regions:
            if region in TELEMETRY_DATA:
                response[region] = analyze_region(
                    TELEMETRY_DATA[region], 
                    threshold_ms
                )
            else:
                response[region] = {
                    "avg_latency": 0,
                    "p95_latency": 0,
                    "avg_uptime": 0,
                    "breaches": 0
                }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            },
            'body': json.dumps(response)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            },
            'body': json.dumps({'error': str(e)})
        }
