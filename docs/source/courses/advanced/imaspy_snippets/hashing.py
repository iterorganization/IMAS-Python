import imas

# 1. Create IDS
eq = imas.IDSFactory().equilibrium()
print(imas.util.calc_hash(eq).hex(' ', 2))  # 2d06 8005 38d3 94c2

# 2. Update homogeneous_time
eq.ids_properties.homogeneous_time = 0
print(imas.util.calc_hash(eq).hex(' ', 2))  # 3b9b 9297 56a2 42fd
# Yes: the hash changed (significantly!). This was expected, because the data is no
# longer the same

# 3. Resize time_slice
eq.time_slice.resize(2)
print(imas.util.calc_hash(eq.time_slice[0]).hex(' ', 2))  # 2d06 8005 38d3 94c2
print(imas.util.calc_hash(eq.time_slice[1]).hex(' ', 2))  # 2d06 8005 38d3 94c2
# What do you notice?
#
#   The hashes of both time_slice[0] and time_slice[1] are identical, because both
#   contain no data.
#
#   The hashes are also identical to the empty IDS hash from step 1. An IDS, or a
#   structure within an IDS, that has no fields filled will always have this hash value.

# 4. Resize profiles_2d
eq.time_slice[0].profiles_2d.resize(1)
p2d = eq.time_slice[0].profiles_2d[0]

# 5. Fill data
p2d.r = [[1., 2.]]
p2d.z = p2d.r
print(imas.util.calc_hash(p2d.r).hex(' ', 2))  # 352b a6a6 b40c 708d
print(imas.util.calc_hash(p2d.z).hex(' ', 2))  # 352b a6a6 b40c 708d
# These hashes are identical, because they contain the same data

# 6. Only r or z
del p2d.z
print(imas.util.calc_hash(p2d).hex(' ', 2))  # 0dcb ddaa 78ea 83a3
p2d.z = p2d.r
del p2d.r
print(imas.util.calc_hash(p2d).hex(' ', 2))  # f86b 8ea8 9652 3768
# Although the data inside `r` and `z` is identical, we get different hashes because the
# data is in a different attribute.
