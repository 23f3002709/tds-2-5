from http.server import BaseHTTPRequestHandler
import json
import statistics

# Load telemetry data from file
def load_telemetry():
    try:
        with open('q-vercel-latency.json', 'r') as f:
            return json.load(f)
    except:
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

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests for latency analysis"""
        # Enable CORS
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        try:
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            request_data = json.loads(body)
            
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
            
            # Send response
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            error_response = {"error": str(e)}
            self.wfile.write(json.dumps(error_response).encode())
