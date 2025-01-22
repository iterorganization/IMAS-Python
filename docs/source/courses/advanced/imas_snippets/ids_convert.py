import imas
from imas.util import get_data_dictionary_version

# 1. Create an IDSFactory for DD 3.25.0
factory = imas.IDSFactory("3.25.0")

# 2. Create a pulse_schedule IDS
pulse_schedule = factory.new("pulse_schedule")
print(get_data_dictionary_version(pulse_schedule))  # This should print 3.25.0

# 3. Fill the IDS with some test data
pulse_schedule.ids_properties.homogeneous_time = \
    imas.ids_defs.IDS_TIME_MODE_HOMOGENEOUS
pulse_schedule.ids_properties.comment = \
    "Testing renamed IDS nodes with imas-python"
pulse_schedule.time = [1., 1.1, 1.2]

pulse_schedule.ec.antenna.resize(1)
antenna = pulse_schedule.ec.antenna[0]
antenna.name = "ec.antenna[0].name in DD 3.25.0"
antenna.launching_angle_pol.reference_name = \
    "ec.antenna[0].launching_angle_pol.reference_name in DD 3.25.0"
antenna.launching_angle_pol.reference.data = [2.1, 2.2, 2.3]
antenna.launching_angle_tor.reference_name = \
    "ec.antenna[0].launching_angle_tor.reference_name in DD 3.25.0"
antenna.launching_angle_tor.reference.data = [3.1, 3.2, 3.3]

# 4. Convert the IDS from version 3.25.0 to 3.39.0
pulse_schedule_3_39 = imas.convert_ids(pulse_schedule, "3.39.0")

# Check that the data is converted
imas.util.print_tree(pulse_schedule_3_39)

# 5. Update time data
pulse_schedule.time[1] = 3
# Yes, the time array of the converted IDS is updated as well:
print(pulse_schedule_3_39.time)  # [1., 3., 1.2]

# 6. Update ids_properties/comment
pulse_schedule.ids_properties.comment = "Updated comment"
print(pulse_schedule_3_39.ids_properties.comment)
# What do you notice?
#   This prints the original value of the comment ("Testing renamed IDS
#   nodes with imas-python").
# This is actually the same that you get when creating a shallow copy
# with ``copy.copy`` of a regular Python dictionary:
import copy

dict1 = {"a list": [1, 1.1, 1.2], "a string": "Some text"}
dict2 = copy.copy(dict1)
print(dict2)  # {"a list": [1, 1.1, 1.2], "a string": "Some text"}
# dict2 is a shallow copy, so dict1["a_list"] and dict2["a_list"] are
# the exact same object, and updating it is reflected in both dicts:
dict1["a list"][1] = 3
print(dict2)  # {"a list": [1, 3, 1.2], "a string": "Some text"}
# Replacing a value in one dict doesn't update the other:
dict1["a string"] = "Some different text"
print(dict2)  # {"a list": [1, 3, 1.2], "a string": "Some text"}

# 7. Set phase.reference_name:
pulse_schedule.ec.antenna[0].phase.reference_name = "Test refname"
# And convert again
pulse_schedule_3_39 = imas.convert_ids(pulse_schedule, "3.39.0")
imas.util.print_tree(pulse_schedule_3_39)
# What do you notice?
#   Element 'ec/antenna/phase' does not exist in the target IDS. Data is not copied.
