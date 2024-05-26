
import sys 
import os
sys.path.insert(1, os.path.join("..",".."))
import pykep as pk
import paseos
from paseos import ActorBuilder, SpacecraftActor
from utils import s2pix_detector, acquire_data
from paseos.utils.load_default_cfg import load_default_cfg
import asyncio
import urllib.request
import matplotlib.pyplot as plt
from matplotlib import patches


#Define today as pykep epoch (27-10-22)
#please, refer to https://esa.github.io/pykep/documentation/core.html#pykep.epoch
today = pk.epoch_from_string('2022-10-27 12:00:00.000')

# Define local actor
S2B = ActorBuilder.get_actor_scaffold(name="Sentinel2-B", actor_type=SpacecraftActor, epoch=today)


sentinel2B_line1 = "1 42063U 17013A   22300.18652110  .00000099  00000+0  54271-4 0  9998"
sentinel2B_line2 = "2 42063  98.5693  13.0364 0001083 104.3232 255.8080 14.30819357294601"

ActorBuilder.set_TLE(S2B, sentinel2B_line1, sentinel2B_line2)


ActorBuilder.set_power_devices(actor=S2B, 
                               battery_level_in_Ws=10080000, 
                               max_battery_level_in_Ws=10080000, 
                               charging_rate_in_W=1860)


cfg=load_default_cfg() # loading cfg to modify defaults
cfg.sim.start_time=today.mjd2000 * pk.DAY2SEC # convert epoch to seconds
cfg.sim.activity_timestep = 0.5 # update rate for plots. 
sim = paseos.init_sim(S2B, cfg)


if not(os.path.isfile("Etna_00.tif")):
    print("Downloading the file: Etna_00.tif")
    urllib.request.urlretrieve("https://actcloud.estec.esa.int/actcloud/index.php/s/9Tw5pEbGbVO3Ttt/download", "Etna_00.tif")
if not(os.path.isfile("La_Palma_02.tif")):
    print("Downloading the file: La_Palma_02.tif")
    urllib.request.urlretrieve("https://actcloud.estec.esa.int/actcloud/index.php/s/vtObKJOuYLgdPf4/download", "La_Palma_02.tif")
if not(os.path.isfile("Mayon_02.tif")):
    print("Downloading the file: Mayon_02.tif")
    urllib.request.urlretrieve("https://actcloud.estec.esa.int/actcloud/index.php/s/e0MyilW1plYdehL/download", "Mayon_02.tif")


# Plot current status of PASEOS and get a plotter
plotter = paseos.plot(sim, paseos.PlotType.SpacePlot)


async def acquire_data_async(args):
    #Fetch the input
    image_path=args[0]
    #Reading the TIF file and returning the image and its coordinates respectively as numpy array and dictionary. 
    #Please, refer to utils.py.
    img, img_coordinates=acquire_data(image_path) 
    #Store results
    args[1][0], args[2][0]=img, img_coordinates
    await asyncio.sleep(3.6) #Acquisition for an L0 granule takes 3.6 seconds for S2B. 


data_acquired=[] #List of acquired images
data_acquired_coordinates=[] #List of image coordinates


# Constraint function
async def constraint_func_async(args):
    plotter.update(sim)
    return True # We impose no practical abort constraint


# Register an activity that emulate data acquisition
sim.register_activity(
    "data_acquisition", activity_function=acquire_data_async, 
    power_consumption_in_watt=266, constraint_function=constraint_func_async
)


output_event_bbox_info = [] # List of output bbox info

async def detect_volcanic_eruptions_async(args):
    # Fetch the inputs
    image, image_coordinates = args[0][0],args[1][0]
    # Detecting volcanic eruptions, returning their bounding boxes and their coordinates.
    #Please, refer to utils.py.
    bbox = s2pix_detector(image, image_coordinates)
    # Store result
    args[2][0] = bbox
    await asyncio.sleep(1) #Assuming one second processing for the cropped tile.


# Register an activity that emulate event detection
sim.register_activity(
    "volcanic_event_detection",
    activity_function=detect_volcanic_eruptions_async,
    power_consumption_in_watt=10,
    constraint_function=constraint_func_async
)


async def idle_state_async(idle_time_s):
    await asyncio.sleep(idle_time_s[0])


# Register an activity that emulate an idle state.
sim.register_activity(
    "idle_state", 
    activity_function=idle_state_async, 
    power_consumption_in_watt=20000, 
    constraint_function=constraint_func_async,
)


data_to_acquire=["Etna_00.tif", "La_Palma_02.tif", "Mayon_02.tif"]


#Data acquisition and processing
print("Scroll up and take a look at the plotter.")

for n, data_name in zip(range(len(data_to_acquire)), data_to_acquire):
    
    #Defining temporary variables to store results of activity functions
    data_acquired_tmp=[None]
    data_acquired_coordinates_tmp=[None]
    output_event_bbox_info_tmp=[None]
    
    # Run the activity
    sim.perform_activity("idle_state", activity_func_args=[10])
    #await sim.wait_for_activity()
    
    #Run the activity
    sim.perform_activity("data_acquisition", activity_func_args=[data_name, data_acquired_tmp, data_acquired_coordinates_tmp])
    #await sim.wait_for_activity()

    #Run the activity
    sim.perform_activity("volcanic_event_detection", activity_func_args=[data_acquired_tmp, data_acquired_coordinates_tmp, output_event_bbox_info_tmp])
    #await sim.wait_for_activity()

    #Storing results of the current iteration
    data_acquired.append(data_acquired_tmp)
    data_acquired_coordinates.append(data_acquired_coordinates_tmp)
    output_event_bbox_info.append(output_event_bbox_info_tmp)
    
# Updating the plotter outside to show the final state after performing the activities
plotter.update(sim)


bboxes, bbox_coordinates = output_event_bbox_info[n][0][0], output_event_bbox_info[n][0][1]


for n in range(3):
    ax[n].imshow(data_acquired[n][0])
    
    bboxes, bbox_coordinates = output_event_bbox_info[n][0][0], output_event_bbox_info[n][0][1]
    for bbox in bboxes:
        bbox=bbox.bbox
        rect = patches.Rectangle((bbox[1], bbox[0]), abs(bbox[1]-bbox[3]), abs(bbox[0]-bbox[2]), linewidth=1, edgecolor='y', facecolor='none')
        ax[n].add_patch(rect)
    
    for coords in bbox_coordinates:
        print("ALERT! Eruption found at: \n\t Top left corner(lon, lat): "+str(coords[0]) +"\n\t bottom right corner(lon, lat): "+str(coords[1])+"\n")
    print("\n")