from pathlib import Path
import os
from abc import ABC, abstractmethod
from Bio import SeqIO
import random
import numpy as np
from rich.progress import track
from hierarchicalsoftmax import SoftmaxNode
from corgi.seqtree import SeqTree
import tarfile
import torch
from io import StringIO
from torchapp.cli import CLIApp, tool, method
import typer

from .data import read_memmap, RANKS


def set_validation_rank_to_seqtree(
    seqtree:SeqTree,
    validation_rank:str="species",
    partitions:int=5,
) -> SeqTree:
    # find the taxonomic rank to use for the validation partition
    validation_rank = validation_rank.lower()
    assert validation_rank in RANKS
    validation_rank_index = RANKS.index(validation_rank)

    partitions_dict = {}
    for key in seqtree:
        node = seqtree.node(key)             
        # Assign validation partition at set rank
        partition_node = node.ancestors[validation_rank_index]
        if partition_node not in partitions_dict:
            partitions_dict[partition_node] = random.randint(0,partitions-1)

        seqtree[key].partition = partitions_dict[partition_node]

    return seqtree


def get_key(accession:str, gene:str) -> str:
    """ Returns the standard format of a key """
    # assert len(accession) == len("RS_GCF_000006945.2")
    key = f"{accession}/{gene}"
    return key


def get_node(lineage:str, lineage_to_node:dict[str,SoftmaxNode]) -> SoftmaxNode:
    if lineage in lineage_to_node:
        return lineage_to_node[lineage]

    split_point = lineage.rfind(";")
    parent_lineage = lineage[:split_point]
    name = lineage[split_point+1:]
    parent = get_node(parent_lineage, lineage_to_node)
    node = SoftmaxNode(name=name, parent=parent)
    lineage_to_node[lineage] = node
    return node


class Embedding(CLIApp, ABC):
    @abstractmethod
    def embed(self, seq:str) -> torch.Tensor:
        """ Takes a protein sequence as a string and returns an embedding vector. """
        pass

    def __call__(self, seq:str) -> torch.Tensor:
        """ Takes a protein sequence as a string and returns an embedding vector. """
        return self.embed(seq)
    
    @method
    def setup(self, **kwargs):
        pass

    def build_seqtree(self, taxonomy:Path) -> tuple[SeqTree,dict[str,SoftmaxNode]]:
        # Create root of tree
        lineage_to_node = {}
        root = None

        # Fill out tree with taxonomy
        accession_to_node = {}
        with open(taxonomy) as f:
            for line in f:
                accesssion, lineage = line.split("\t")

                if not root:
                    root_name = lineage.split(";")[0]
                    root = SoftmaxNode(root_name)
                    lineage_to_node[root_name] = root

                node = get_node(lineage, lineage_to_node)
                accession_to_node[accesssion] = node
        
        seqtree = SeqTree(classification_tree=root)
        return seqtree, accession_to_node

    @tool("setup")
    def build_gene_array(
        self,
        marker_genes:Path=typer.Option(default=..., help="The path to the marker genes tarball (e.g. bac120_msa_marker_genes_all_r220.tar.gz)."),
        family_index:int=typer.Option(default=..., help="The index for the gene family to use. E.g. if there are 120 gene families then this should be a number from 0 to 119."),
        output_dir:Path=typer.Option(default=..., help="A directory to store the output which includes the memmap array, the listing of accessions and an error log."),
        flush_every:int=typer.Option(default=5_000, help="An interval to flush the memmap array as it is generated."),
        **kwargs,
    ):
        self.setup(**kwargs)

        assert marker_genes is not None
        assert family_index is not None
        assert output_dir is not None

        dtype = 'float16'

        memmap_wip_array = None
        output_dir.mkdir(parents=True, exist_ok=True)
        memmap_wip_path = output_dir / f"{family_index}-wip.npy"
        error = output_dir / f"{family_index}-errors.txt"
        accessions_wip = output_dir / f"{family_index}-accessions-wip.txt"

        accessions = []
        
        print(f"Loading {marker_genes} file.")
        with tarfile.open(marker_genes, "r:gz") as tar, open(error, "w") as error_file, open(accessions_wip, "w") as accessions_wip_file:
            members = [member for member in tar.getmembers() if member.isfile() and member.name.endswith(".faa")]
            prefix_length = len(os.path.commonprefix([Path(member.name).with_suffix("").name for member in members]))
            
            member = members[family_index]
            print(f"Processing file {family_index} in {marker_genes}")

            f = tar.extractfile(member)
            marker_id = Path(member.name).with_suffix("").name[prefix_length:]

            fasta_io = StringIO(f.read().decode('ascii'))

            total = sum(1 for _ in SeqIO.parse(fasta_io, "fasta"))
            fasta_io.seek(0)
            print(marker_id, total)
    
            for record in track(SeqIO.parse(fasta_io, "fasta"), total=total):
            # for record in SeqIO.parse(fasta_io, "fasta"):
                species_accession = record.id
                                
                key = get_key(species_accession, marker_id)

                seq = str(record.seq).replace("-","").replace("*","")
                try:
                    vector = self(seq)
                except Exception as err:
                    print(f"{key} ({len(seq)}): {err}", file=error_file)
                    continue

                if vector is None:
                    print(f"{key} ({len(seq)}): Embedding is None", file=error_file)
                    continue

                if torch.isnan(vector).any():
                    print(f"{key} ({len(seq)}): Embedding contains NaN", file=error_file)
                    continue

                if memmap_wip_array is None:
                    size = len(vector)
                    shape = (total,size)
                    memmap_wip_array = np.memmap(memmap_wip_path, dtype=dtype, mode='w+', shape=shape)

                index = len(accessions)
                memmap_wip_array[index,:] = vector.cpu().half().numpy()
                if index % flush_every == 0:
                    memmap_wip_array.flush()
                
                accessions.append(key)
                print(key, file=accessions_wip_file)
                                            
        memmap_wip_array.flush()

        accessions_path = output_dir / f"{family_index}.txt"
        with open(accessions_path, "w") as f:
            for accession in accessions:
                print(accession, file=f)
        
        # Save final memmap array now that we now the final size
        memmap_path = output_dir / f"{family_index}.npy"
        shape = (len(accessions),size)
        print(f"Writing final memmap array of shape {shape}: {memmap_path}")
        memmap_array = np.memmap(memmap_path, dtype=dtype, mode='w+', shape=shape)
        memmap_array[:len(accessions),:] = memmap_wip_array[:len(accessions),:]
        memmap_array.flush()

        # Clean up
        memmap_array._mmap.close()
        memmap_array._mmap = None
        memmap_array = None
        memmap_wip_path.unlink()
        accessions_wip.unlink()

    @tool
    def set_validation_rank(
        self,
        seqtree:Path=typer.Option(default=..., help="The path to the seqtree file."),
        output:Path=typer.Option(default=..., help="The path to save the adapted seqtree file."),
        validation_rank:str=typer.Option(default="species", help="The rank to hold out for cross-validation."),
        partitions:int=typer.Option(default=5, help="The number of cross-validation partitions."),
    ) -> SeqTree:
        seqtree = SeqTree.load(seqtree)
        set_validation_rank_to_seqtree(seqtree, validation_rank=validation_rank, partitions=partitions)
        seqtree.save(output)
        return seqtree

    @tool
    def preprocess(
        self,
        taxonomy:Path=typer.Option(default=..., help="The path to the TSV taxonomy file (e.g. bac120_taxonomy_r220.tsv)."),
        marker_genes:Path=typer.Option(default=..., help="The path to the marker genes tarball (e.g. bac120_msa_marker_genes_all_r220.tar.gz)."),
        output_dir:Path=typer.Option(default=..., help="A directory to store the output which includes the memmap array, the listing of accessions and an error log."),
        partitions:int=typer.Option(default=5, help="The number of cross-validation partitions."),
        seed:int=typer.Option(default=42, help="The random seed."),
    ):
        seqtree, accession_to_node = self.build_seqtree(taxonomy)

        dtype = 'float16'

        random.seed(seed)

        print(f"Loading {marker_genes} file.")
        with tarfile.open(marker_genes, "r:gz") as tar:
            members = [member for member in tar.getmembers() if member.isfile() and member.name.endswith(".faa")]
            family_count = len(members)
        print(f"{family_count} gene families found.")

        # Read and collect accessions
        print(f"Building seqtree")
        keys = []
        counts = []
        for family_index in track(range(family_count)):
            keys_path = output_dir / f"{family_index}.txt"

            with open(keys_path) as f:
                family_index_keys = [line.strip() for line in f]
                keys += family_index_keys
                counts.append(len(family_index_keys))

                for key in family_index_keys:
                    species_accession = key.split("/")[0]
                    node = accession_to_node[species_accession]
                    partition = random.randint(0,partitions-1)

                    # Add to seqtree
                    seqtree.add(key, node, partition)
        
        # Save seqtree
        seqtree_path = output_dir / f"{output_dir.name}.st"
        print(f"Saving seqtree to {seqtree_path}")
        seqtree.save(seqtree_path)

        # Concatenate numpy memmap arrays
        memmap_array = None
        memmap_array_path = output_dir / f"{output_dir.name}.npy"
        print(f"Saving memmap to {memmap_array_path}")
        current_index = 0
        for family_index, family_count in track(enumerate(counts), total=len(counts)):
            my_memmap_path = output_dir / f"{family_index}.npy"

            # Build memmap for gene family if it doesn't exist
            if not my_memmap_path.exists():
                print("Building", my_memmap_path)
                self.build_gene_array(marker_genes=marker_genes, family_index=family_index, output_dir=output_dir)
                assert my_memmap_path.exists()

            my_memmap = read_memmap(my_memmap_path, family_count)

            # Build memmap for output if it doesn't exist
            if memmap_array is None:
                size = my_memmap.shape[1]
                shape = (len(keys),size)
                memmap_array = np.memmap(memmap_array_path, dtype=dtype, mode='w+', shape=shape)

            # Copy memmap for gene family into output memmap
            memmap_array[current_index:current_index+family_count,:] = my_memmap[:,:]

            current_index += family_count

        assert len(keys) == current_index

        memmap_array.flush()

        # Save keys
        keys_path = output_dir / f"{output_dir.name}.txt"
        print(f"Saving keys to {keys_path}")        
        with open(keys_path, "w") as f:
            for key in keys:
                print(key, file=f)

