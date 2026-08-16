import sys
import os
import traceback

# Add the application directory to the system path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from app import app as application
except Exception as e:
    # Write the traceback to wsgi_error.log in the same directory for debugging
    log_file = os.path.join(os.path.dirname(__file__), 'wsgi_error.log')
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("Startup Error Traceback:\n")
            traceback.print_exc(file=f)
    except Exception:
        pass
    # Re-raise the exception for the WSGI server
    raise e
