import imas

# 1. Create an empty distributions IDS
distributions = imas.IDSFactory().distributions()

# 2. Use the metadata attribute to find the coordinates of
#    distribution/profiles_2d/density
print(distributions.metadata["distribution/profiles_2d/density"].coordinates)
# Alternative, by resizing the Arrays of Structures:
distributions.distribution.resize(1)
distributions.distribution[0].profiles_2d.resize(1)
p2d = distributions.distribution[0].profiles_2d[0]
print(p2d.density.metadata.coordinates)
# This outputs (newlines added for clarity):
#  (IDSCoordinate('distribution(i1)/profiles_2d(itime)/grid/r
#                  OR distribution(i1)/profiles_2d(itime)/grid/rho_tor_norm'),
#   IDSCoordinate('distribution(i1)/profiles_2d(itime)/grid/z
#                  OR distribution(i1)/profiles_2d(itime)/grid/theta_geometric
#                  OR distribution(i1)/profiles_2d(itime)/grid/theta_straight'))
#
# What do you notice: in both dimensions there are multiple options for the coordinate.

# 3. Retrieve the coordinate values through the ``coordinates`` attribute.
# This will raise a coordinate lookup error because imas-python cannot choose which of the
# coordinates to use:
try:
    print(p2d.density.coordinates[0])
except Exception as exc:
    print(exc)

# 4a. Use the IDSCoordinate.references attribute:
# Example for the first dimension:
coordinate_options = p2d.density.metadata.coordinates[0].references
# 4b. Use IDSPath.goto:
for option in coordinate_options:
    coordinate_node = option.goto(p2d.density)
    print(coordinate_node)
# This will print:
#   <IDSNumericArray (IDS:distributions, distribution[0]/profiles_2d[0]/grid/r, empty FLT_1D)>
#   <IDSNumericArray (IDS:distributions, distribution[0]/profiles_2d[0]/grid/rho_tor_norm, empty FLT_1D)>
