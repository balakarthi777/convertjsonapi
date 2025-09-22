Manual Steps
You may use this repository directly or create your own repository from this template if you'd like to customize the code.

Create a new Web Service on Render.

Specify the URL to your new repository or this repository.

Render will automatically detect that you are deploying a Python service and use pip to download the dependencies.

Specify the following as the Start Command.

uvicorn main:app --host 0.0.0.0 --port $PORT
Click Create Web Service.

 
