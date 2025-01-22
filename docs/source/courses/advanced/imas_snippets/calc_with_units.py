import itertools  # python standard library iteration tools

import imas
import imas.training
import pint

# 1. Load core_profiles IDS from training DBEntry
entry = imas.training.get_training_db_entry()
cp = entry.get("core_profiles")

# 2. Select the first time slice of profiles_1d
p1d = cp.profiles_1d[0]

# 3.
# Create pint UnitRegistry
ureg = pint.UnitRegistry()

# Convert DD units to Pint Units
_dd_to_pint = {
    "-": ureg("dimensionless"),
    "Atomic Mass Unit": ureg("unified_atomic_mass_unit"),
    "Elementary Charge Unit": ureg("elementary_charge"),
}
def dd_to_pint(dd_unit):
    if dd_unit in _dd_to_pint:
        return _dd_to_pint[dd_unit]
    return ureg(dd_unit)
# End of translation

# 4. Calculate mass density:
# 4a. Create mass_density variable with units:
mass_density = ureg("0 kg.m^-3")
# 4b. Loop over all ion and neutral species
for species in itertools.chain(p1d.ion, p1d.neutral):
    mass = sum(
        element.a * dd_to_pint(element.a.metadata.units)
        for element in species.element
    )
    density = species.density * dd_to_pint(species.density.metadata.units)
    mass_density += mass * density

# 4c. Print the total mass density
print(mass_density)
# Note that the species mass is given in Atomic Mass Units, but pint
# automatically converted this to kilograms for us, because we defined
# mass_density in kg/m^3!
