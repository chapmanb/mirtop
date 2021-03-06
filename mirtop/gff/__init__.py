"""GFF proxy converter"""
from __future__ import print_function

import os.path as op

from mirtop.mirna import fasta, mapper
from mirtop.bam.bam import read_bam
from mirtop.importer import seqbuster, srnabench, prost, isomirsea
from mirtop.mirna.annotate import annotate
from mirtop.gff import body, header, merge
import mirtop.libs.logger as mylog
logger = mylog.getLogger(__name__)


def reader(args):
    """
    Realign BAM hits to miRBAse to get better accuracy and annotation
    """
    samples = []
    database = mapper.guess_database(args.gtf)
    args.database = database
    precursors = fasta.read_precursor(args.hairpin, args.sps)
    args.precursors = precursors
    matures = mapper.read_gtf_to_precursor(args.gtf)
    args.matures = matures
    # TODO check numbers of miRNA and precursors read
    # TODO print message if numbers mismatch
    out_dts = dict()
    for fn in args.files:
        if args.format != "gff":
            sample = op.splitext(op.basename(fn))[0]
            samples.append(sample)
            fn_out = op.join(args.out, sample + ".%s" % args.out_format)
        if args.format == "BAM":
            reads = _read_bam(fn, args)
        elif args.format == "seqbuster":
            reads = seqbuster.read_file(fn, args)
        elif args.format == "srnabench":
            out_dts[fn] = srnabench.read_file(fn, args)
        elif args.format == "prost":
            reads = prost.read_file(fn, precursors, database, args.gtf)
        elif args.format == "isomirsea":
            out_dts[fn] = isomirsea.read_file(fn, args)
        elif args.format == "gff":
            samples.extend(header.read_samples(fn))
            out_dts[fn] = body.read(fn, args)
            continue
        if args.format not in ["isomirsea", "srnabench"]:
            ann = annotate(reads, matures, precursors)
            out_dts[fn] = body.create(ann, database, sample, args)
        h = header.create([sample], database, "")
        _write(out_dts[fn], h, fn_out)
    # merge all reads for all samples into one dict
    merged = merge.merge(out_dts, samples)
    fn_merged_out = op.join(args.out, "mirtop.%s" % args.out_format)
    _write(merged, header.create(samples, database, ""), fn_merged_out)


def _write(lines, header, fn):
    out_handle = open(fn, 'w')
    print(header, file=out_handle)
    for m in lines:
        for s in sorted(lines[m].keys()):
            for hit in lines[m][s]:
                print(hit[4], file=out_handle)
    out_handle.close()


def _read_bam(bam_fn, precursors):
    if bam_fn.endswith("bam") or bam_fn.endswith("sam"):
        logger.info("Reading %s" % bam_fn)
        reads = read_bam(bam_fn, precursors)
    else:
        raise ValueError("Format not recognized."
                         " Only working with BAM/SAM files.")
    return reads
