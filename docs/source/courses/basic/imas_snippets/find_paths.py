import imas.util

factory = imas.IDSFactory()
core_profiles = factory.core_profiles()

print("Paths containing `rho`:")
print(imas.util.find_paths(core_profiles, "rho"))
print()

print("Paths containing `rho`, not followed by `error`:")
print(imas.util.find_paths(core_profiles, "rho(?!.*error)"))
print()

print("All paths ending with `time`:")
print(imas.util.find_paths(core_profiles, "time$"))
print()
