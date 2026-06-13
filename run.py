"""
SwtchTech POS System - Startup Script
Run this file to start the system.
"""
from app import app, init_db

if __name__ == '__main__':
    init_db()
    print("\n" + "="*50)
    print("  SWTCH TECH POS SYSTEM")
    print("  Master Your Digital Universe")
    print("="*50)
    print("\n  System starting at: http://localhost:5000")
    print("  Admin login:  admin / admin123")
    print("  Sales login:  sales1 / sales123")
    print("\n  Press CTRL+C to stop\n")
    app.run(debug=False, host='0.0.0.0', port=5000)
