from flask import Flask, render_template
import logging

app = Flask(__name__)

@app.route('/')
def dashboard():
    """Display the dashboard for GUI management."""
    try:
        return render_template('dashboard.html')
    except Exception as e:
        logging.error(f"Error rendering dashboard: {e}")
        raise

if __name__ == "__main__":
    app.run(debug=True)
