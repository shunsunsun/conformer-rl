# %%

from rdkit import Chem
from rdkit.Chem import Draw
import stk
from itertools import cycle, islice
from IPython.display import display
from stk.molecular.atoms import atom_info
from stko.molecular.molecules.constructed_molecule_torsioned import ConstructedMoleculeTorsioned
from stko.molecular.torsions.torsion import Torsion

class XorGate:
    """
    >>> xor_gate = XorGate(gate_complexity=2, num_gates=3)
    >>> xor_gate.get_torsions()
    [[1, 0, 7, 8],
    [10, 9, 14, 15],
    [17, 16, 21, 22],
    [25, 26, 28, 29],
    [32, 33, 35, 36],
    [39, 40, 42, 43]]
    >>> xor_gate.num_torsions == xor_gate.num_gates * xor_gate.gate_complexity
    True
    >>> xor_gate.get_individual_gate().num_gates
    1
    >>> xor_gate.get_individual_gate().gate_complexity
    2
    """
    def __init__(self, gate_complexity, num_gates):
        # use stk to construct an XOR gate molecule to design specifications
        self.gate_complexity = gate_complexity
        self.num_gates = num_gates
        self.num_torsions = num_gates * gate_complexity

        # construct XOR gate monomers
        xor_gate_top, top_building_block = self.make_xor_individual_gate(*self.make_xor_monomer(position=0))
        xor_gate_bottom, bottom_building_block = self.make_xor_individual_gate(*self.make_xor_monomer(position=3))
        
        # Example: for num_gates == 5, gives 'ABABA'
        monomer_pattern = ''.join(islice(cycle('A' + 'B'), num_gates))
        self.polymer = stk.ConstructedMolecule(
            topology_graph=stk.polymer.Linear(
                building_blocks=(top_building_block, bottom_building_block),
                repeating_unit=monomer_pattern,
                num_repeating_units=1,
            )
        )
        self.polymer = ConstructedMoleculeTorsioned(self.polymer)
        self.polymer.transfer_torsions({top_building_block : xor_gate_top,
                                        bottom_building_block : xor_gate_bottom})

    def make_xor_individual_gate(self, xor_monomer, xor_building_block):
        individual_gate = stk.ConstructedMolecule(
            topology_graph=stk.polymer.Linear(
                building_blocks=(xor_building_block,),
                repeating_unit='A',
                num_repeating_units=self.gate_complexity
            )
        )
        display(Draw.MolToImage(mol_with_atom_index(
            individual_gate.to_rdkit_mol()), size=(700, 300)))
        
        individual_gate = ConstructedMoleculeTorsioned(individual_gate)
        individual_gate.transfer_torsions({xor_building_block: xor_monomer})
            
        # construct the functional groups of the gate from the functional groups of the monomers
        functional_groups = list(xor_building_block.get_functional_groups())
        atom_maps = individual_gate.atom_maps
        functional_groups = [functional_groups[0].with_atoms(atom_maps[0]),
                             functional_groups[1].with_atoms(atom_maps[self.gate_complexity - 1])]
        
        gate_building_block = stk.BuildingBlock.init_from_molecule(individual_gate.stk_molecule,
                                                                   functional_groups)
        return individual_gate, gate_building_block

    def make_xor_monomer(self, position=0):
        # initialize building blocks
        benzene = init_building_block(smiles='C1=CC=CC=C1')
        acetaldehyde = init_building_block(smiles='CC=O')
        benzene = benzene.with_functional_groups([stk.SingleAtom(stk.C(position))])
        acetaldehyde = acetaldehyde.with_functional_groups(
            [stk.SingleAtom(stk.C(1))])

        # construct xor gate monomer
        xor_monomer = stk.ConstructedMolecule(
            topology_graph=stk.polymer.Linear(
                building_blocks=(benzene, acetaldehyde),
                repeating_unit='AB',
                num_repeating_units=1
            )
        )
        xor_monomer = ConstructedMoleculeTorsioned(xor_monomer)
        
        # set the initial torsions
        if position == 0:
            xor_monomer.set_torsions([Torsion(stk.C(1), stk.C(0), stk.C(7), stk.C(6))])
        elif position == 3:
            xor_monomer.set_torsions([Torsion(stk.C(2), stk.C(3), stk.C(7), stk.C(6))])

        # construct functional groups for xor gate monomer
        # numbering starts at top and proceeds clockwise
        c_0, c_1, c_2, c_3, c_4, c_5 = stk.C(0), stk.C(
            1), stk.C(2), stk.C(3), stk.C(4), stk.C(5)
        functional_groups = [stk.GenericFunctionalGroup(atoms=(c_0, c_3, c_4, c_5),
                                                        bonders=(c_0, c_3), deleters=(c_4, c_5)),
                            stk.GenericFunctionalGroup(atoms=(c_1, c_2),
                                                        bonders=(c_1, c_2), deleters=())]
        xor_building_block = stk.BuildingBlock.init_from_molecule(xor_monomer.stk_molecule,
                                                                  functional_groups)
        return xor_monomer, xor_building_block

    def get_torsions(self):
        'returns a list torsions in the molecule, where each torsion is a list of atom indices'
        mon_size = 7
        num_atoms = self.polymer.get_num_atoms()
        num_top_atoms = num_atoms // 2 + 1
        nonring = [[1, 0, 7, 8]]
        nonring += [[i+1, i, i+5, i+6] for i in range(9, num_top_atoms , mon_size)]
        nonring += [[i-1, i, i+2, i+3] for i in range(num_top_atoms + 3, num_atoms, mon_size)]
        return nonring


    def get_env(self):  # this may involve some environment refactoring
        'returns a gym environment corresponding to this molecule'
        raise NotImplementedError

    def get_individual_gate(self):
        'returns a corresponding XOR gate molecule with a single gate'
        return XorGate(self.gate_complexity, 1)

    def individual_gate_torsion_idx(self, torsion_idx):
        'given a torsion index, returns the corresponding torsion index in an individual gate'
        return torsion_idx % self.gate_complexity


def mol_with_atom_index(mol):
    for atom in mol.GetAtoms():
        atom.SetAtomMapNum(atom.GetIdx())
    return mol

def init_building_block(smiles):
    'construct a building block with hydrogens removed'
    mol = stk.BuildingBlock(smiles=smiles)
    mol = Chem.rdmolops.RemoveHs(mol.to_rdkit_mol(), sanitize=True)
    # convert rdkit aromatic bonds to single and double bonds for portability
    Chem.rdmolops.Kekulize(mol)
    return stk.BuildingBlock.init_from_rdkit_mol(mol)

if __name__ == "__main__":
    # utilize the doctest module to check tests built into the documentation
    import doctest
    import importlib
    import sys
    importlib.reload(sys.modules[
        'stko.molecular.molecules.constructed_molecule_torsioned'])
    from stko.molecular.molecules.constructed_molecule_torsioned import ConstructedMoleculeTorsioned
    # doctest.testmod(optionflags = doctest.NORMALIZE_WHITESPACE, verbose=True)
    
    # visualize the molecule used in the documentation tests
    xor3_gate = XorGate(gate_complexity=3, num_gates=4)
    print('xor3_gate.polymer.get_torsion_infos() =')
    print(*[torsion_info.torsion for torsion_info in xor3_gate.polymer.get_torsion_infos()], sep='\n')
    # xor_gate = XorGate(gate_complexity=2, num_gates=1)
    display(Draw.MolToImage(mol_with_atom_index(xor3_gate.polymer.stk_molecule.to_rdkit_mol()),size=(700,300)))
    # display(Draw.MolToImage(mol_with_atom_index(xor_gate.polymer.to_rdkit_mol()),size=(700,300)))
    
    # test new stk method for getting a corresponding building block atom
    # print(list(xor_gate.polymer.get_atom_infos())[10].get_building_block_atom())

# %%
