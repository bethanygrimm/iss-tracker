<h1>International Space Station Tracker App</h1>

<h2>About</h2>
This project uses data from the International Space Station to track its position and velocity at given times. NASA publishes ISS data multiple times a week, which displays the projected positions and velocities of the ISS in four-minute increments in a multiple-week timeframe. This is a huge amount of data to parse through manually. This software package is designed to parse through this satellite data and return useful data and computations from the dataset.

<h2>Included Files</h2>
<ul>
<li>Dockerfile: used to build the container for this software package</li>
<li>docker-compose.yml: used to facilitate running the containers</li> 
<li>requirements.txt: list of dependencies required to run the containers</li>
<li>iss_tracker.py: contains main and functions used to analyze data. This script utilizes a Flask server such that all commands can be accessed through URL routes.</li>
<li>test_iss_tracker.py: contains unit tests for iss_tracker.py</li>
</ul>

<h2>Accessing Data</h2> 
This program is designed to work using a URL to a dataset in XML format. The program automatically parses data from <a href="https://spotthestation.nasa.gov/trajectory_data.cfm">ISS Trajectory Data</a> and will analyze data from there. Data backups will automatically be saved to a directory "data" on the your local machine.

<h2>Building Container</h2>
Since code is containerized, no installations are required - just a machine that is capable of running Docker containers. First, ensure Dockerfile, docker_compose.yml, requirements.txt, iss_tracker.py, and test_iss_tracker.py are in the same directory. Next, create a directory called "data" within this directory - this is necessary for the Redis container to be able to backup its data. Then, run the command:<br>
<code>docker build -t [username]/iss_tracker:1.0 ./</code><br>
in which [username] is replaced with the user's Docker username.<br>
The container for the Flask app has now been built. 

<h2>Running Container</h2>
Since there are two containers - the Redis database and the Flask app - that need to be coordinated, docker-compose will facilitate building images of both containers.<br>
To run the container with docker-compose, first edit the file docker-compose.yml such that <code>[username]</code> is replaced with your username. Additionally, replace <code>"5000:5000"</code> or <code>"6379:6379"</code> with a different port if their respective ports are already occupied.<br>
Then run the command:<br>
<code>docker compose up -d</code>
Both containers are now running in the background. You may check the status of the containers by running <code>docker ps</code>.

<h2>Running Scripts and Unit Tests with curl</h2>
Once the container is running in the background, the following commands may be run:
<ul>
<li><code>curl localhost:5000/epochs</code></li>
    <ul>
    <li>This route returns the entire dataset in JSON format.</li>
    </ul>
<li><code>curl "localhost:5000/epochs?limit=[limit]&offset=[offset]"</code></li>
    <ul>
    <li>[limit] and [offset] must be integers. This route returns [offset] amount of epochs starting from index [limit]. To get a better sense of the range of data and the number of indices, the route <code>curl localhost:5000/range</code> is also included.</li>
    </ul>
<li><code>curl localhost:5000/[epoch]</code></li>
    <ul>
    <li>[epoch] must be a string, the epoch queried. This route returns all state vectors for the epoch requested (or the closest one). A rather specific string format is needed: %Y-%jT%H:%M:%S.%fZ, that is [year]-[days in year]T[hour]:[minute]:[second].[microsecond]Z (example "2025-32T12:00:00.000Z" for precisely 12:00 on February 1, 2025). The output <code>curl localhost:5000/epochs</code> also gives examples of this epoch format.</li>
    </ul>
<li><code>curl localhost:5000/[epoch]/speed</code></li>
    <ul>
    <li>[epoch] must be a string, the epoch queried. This route returns the instantaneous speed for the epoch requested. This must be in the format %Y-%jT%H:%M:%S.%fZ</li>
    </ul>
<li><code>curl localhost:5000/[epoch]/position</code></li>
    <ul>
    <li>[epoch] must be a string, the epoch queried. This route returns the location information for the epoch requested: latitude, longitude, altitude, and approximate geographic location (with "none" meaning the ISS is above the ocean). This must be in the format %Y-%jT%H:%M:%S.%fZ</li>
<li><code>curl localhost:5000/now</code></li>
    <ul>
    <li>This route returns state vectors, instantaneous speed, and position data for the epoch closest to the current time.</li>
    </ul>
<li><code>curl localhost:5000/range</code></li>
    <ul>
    <li>This route returns information on the number of epochs in the dataset and the times the epochs range from.</li>
    </ul>
</ul>
To execute test_iss_tracker.py, run the command <code>pytest</code>. Pytest is automatically installed in the container build, so all the unit tests for iss_tracker.py should readily run.<br>
The output of test_iss_tracker.py should list ten successes, one for each unit test. Additionally, there may be a warning returned from <code>test_return_state_vectors</code>: the app is designed to use the very first epoch (January 1, 1970) if database cannot be accessed, and Astropy throws a warning if the epoch is from too long ago.<br>

<h2>Exiting Container</h2>
After all the desired scripts have been run, use the following commands to stop and remove the containers:<br>
<code>docker compose down</code><br>

<h2>Software Diagram</h2>
<img src="https://github.com/bethanygrimm/iss-tracker/blob/ad16ffa4427f90b5b2e5ca978009f8d43a9c4cde/ISS%20Tracker%20Software%20Diagram.png" alt="Software Diagram">
Software diagram for this system. The user signs into a virtual machine, and from there is able to build the image of iss_tracker. The containers of iss_tracker and redis can then be run with docker-compose. Both the Flask app and Redis databases are run in tandem; the user can access curl commands with Flask running in the background, and Redis automatically backs up the NASA data to the user's local machine.
<br><br>

<h2>AI Usage</h2>
No AI was used for this project.
