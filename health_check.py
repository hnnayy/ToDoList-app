from flask import jsonify
import time
import psutil
import os

def register_health_routes(app):
    """Register health check routes"""
    
    @app.route('/health')
    def health_check():
        """Basic health check"""
        return jsonify({
            'status': 'healthy',
            'timestamp': time.time(),
            'version': os.getenv('APP_VERSION', '1.0.0')
        })
    
    @app.route('/health/detailed')
    def detailed_health_check():
        """Detailed health check with system metrics"""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time(),
                'metrics': {
                    'cpu_usage_percent': cpu_usage,
                    'memory_usage_percent': memory.percent,
                    'disk_usage_percent': disk.percent,
                    'available_memory_mb': memory.available // (1024*1024)
                }
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': time.time()
            }), 500
