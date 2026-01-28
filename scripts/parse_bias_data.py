import csv
import re
import json
import sys

# Increase CSV field size limit just in case
csv.field_size_limit(sys.maxsize)

# File Paths
EREPO_PATH = "/Users/arunbodd/Documents/Work/AIVA_Benchmarking/AIVA-var-bench/data/erepo-tabbed.tsv"
BIAS_PATH = "/Users/arunbodd/Documents/Work/AIVA_Benchmarking/AIVA-var-bench/bias_v2.0.0_supplementary_files/erepo_feb_2nd_bitscopic_classifications.tsv"
INTERVAR_PATH = "/Users/arunbodd/Documents/Work/AIVA_Benchmarking/AIVA-var-bench/bias_v2.0.0_supplementary_files/erepo_feb_2nd.hg19_multianno.txt.intervar"
OUTPUT_PATH = "/Users/arunbodd/Documents/Work/AIVA_Benchmarking/AIVA-var-bench/data/erepo_bias_intervar_merged.jsonl"

# Mapping NC identifiers to Chromosomes (hg19 / GRCh37)
NC_TO_CHR = {
    "NC_000001.10": "chr1", "NC_000002.11": "chr2", "NC_000003.11": "chr3",
    "NC_000004.11": "chr4", "NC_000005.9": "chr5", "NC_000006.11": "chr6",
    "NC_000007.13": "chr7", "NC_000008.10": "chr8", "NC_000009.11": "chr9",
    "NC_000010.10": "chr10", "NC_000011.9": "chr11", "NC_000012.11": "chr12",
    "NC_000013.10": "chr13", "NC_000014.8": "chr14", "NC_000015.9": "chr15",
    "NC_000016.9": "chr16", "NC_000017.10": "chr17", "NC_000018.9": "chr18",
    "NC_000019.9": "chr19", "NC_000020.10": "chr20", "NC_000021.8": "chr21",
    "NC_000022.10": "chr22", "NC_000023.10": "chrX", "NC_000024.9": "chrY",
    "NC_012920.1": "chrM"
}

def parse_intervar_string(s):
    # s example: "InterVar: Likely pathogenic PVS1=0 PS=[0, 0, 0, 0, 0] ..."
    if not s:
        return "Uncertain Significance", []

    # Regex for classification
    classification = "Uncertain Significance"
    m_class = re.search(r'InterVar:\s+(.+?)\s+PVS1=', s)
    if m_class:
        classification = m_class.group(1).strip()
        # Canonicalize classification
        c_low = classification.lower()
        if "likely pathogenic" in c_low: classification = "Likely Pathogenic"
        elif "pathogenic" in c_low: classification = "Pathogenic"
        elif "likely benign" in c_low: classification = "Likely Benign"
        elif "benign" in c_low: classification = "Benign"
        else: classification = "Uncertain Significance"
    
    criteria = []
    
    # helper to parse array string "[0, 1, ...]"
    def parse_arr(arr_str):
        if not arr_str: return []
        arr_str = arr_str.replace('[', '').replace(']', '')
        try:
            return [int(float(x.strip())) for x in arr_str.split(',') if x.strip()]
        except ValueError:
            return []

    # PVS1
    if "PVS1=1" in s: criteria.append("PVS1")
    
    # PS
    m_ps = re.search(r'PS=\[(.*?)\]', s)
    if m_ps:
        vals = parse_arr(m_ps.group(1))
        for i, v in enumerate(vals):
            if v >= 1: criteria.append(f"PS{i+1}")

    # PM
    m_pm = re.search(r'PM=\[(.*?)\]', s)
    if m_pm:
        vals = parse_arr(m_pm.group(1))
        for i, v in enumerate(vals):
            if v >= 1: criteria.append(f"PM{i+1}")

    # PP
    m_pp = re.search(r'PP=\[(.*?)\]', s)
    if m_pp:
        vals = parse_arr(m_pp.group(1))
        for i, v in enumerate(vals):
            if v >= 1: criteria.append(f"PP{i+1}")
            
    # BA1
    if "BA1=1" in s: criteria.append("BA1")
    
    # BS
    m_bs = re.search(r'BS=\[(.*?)\]', s)
    if m_bs:
        vals = parse_arr(m_bs.group(1))
        for i, v in enumerate(vals):
            if v >= 1: criteria.append(f"BS{i+1}")
            
    # BP
    m_bp = re.search(r'BP=\[(.*?)\]', s)
    if m_bp:
        vals = parse_arr(m_bp.group(1))
        for i, v in enumerate(vals):
            if v >= 1: criteria.append(f"BP{i+1}")
            
    return classification, criteria

def parse_bias_rationale(json_str):
    criteria = []
    if not json_str: return criteria
    try:
        data = json.loads(json_str)
        # categories: pvs, ps, pm, pp, ba, bs, bp
        for cat in data:
            if isinstance(data[cat], dict):
                for code, val in data[cat].items():
                    # val is [score, description]
                    if isinstance(val, list) and len(val) > 0:
                        score = val[0]
                        if score > 0:
                            criteria.append(code.upper())
    except:
        pass
    return criteria

def parse_erepo():
    """Parses Erepo TSV and builds a map from (chrom, pos, ref, alt) -> UUID + Data"""
    print("Parsing EREPO data...")
    coord_map = {}
    
    with open(EREPO_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        count = 0
        for row in reader:
            uuid = row.get('Uuid', '').strip()
            hgvs_exprs = row.get('HGVS Expressions', '')
            
            # Match HGVS for hg19 genomic coords.
            # Handles: NC_XXXX.XX:g.POSREF>ALT
            # Also simpler indel logic: just grab pos and assume complex match later
            
            matches = re.finditer(r'(NC_\d+\.\d+):g\.(\d+)(?:_(\d+))?([A-Za-z0-9>]+)', hgvs_exprs)
            
            extracted = False
            for m in matches:
                acc = m.group(1)
                if acc in NC_TO_CHR:
                    chrom = NC_TO_CHR[acc]
                    start = int(m.group(2))
                    rest = m.group(4) 
                    
                    if '>' in rest and 'del' not in rest and 'ins' not in rest and 'dup' not in rest:
                        try:
                            ref, alt = rest.split('>')
                            key = (chrom, start, ref, alt)
                            if key not in coord_map: coord_map[key] = []
                            coord_map[key].append({"uuid": uuid, "row": row})
                            extracted = True
                        except ValueError:
                            pass 
                    else:
                        # Indel or complex, just register chrom,start
                        key_complex = (chrom, start, "COMPLEX", "COMPLEX")
                        if key_complex not in coord_map: coord_map[key_complex] = []
                        coord_map[key_complex].append({"uuid": uuid, "row": row})
                        extracted = True

            # If failed to extract via regex, check if it's an indel with 'del' 'ins' keywords
            if not extracted:
                 # Backup regex for explicits like del/ins
                 matches_indel = re.finditer(r'(NC_\d+\.\d+):g\.(\d+)', hgvs_exprs)
                 for m in matches_indel:
                     acc = m.group(1)
                     if acc in NC_TO_CHR:
                         chrom = NC_TO_CHR[acc]
                         start = int(m.group(2))
                         key_complex = (chrom, start, "COMPLEX", "COMPLEX")
                         if key_complex not in coord_map: coord_map[key_complex] = []
                         coord_map[key_complex].append({"uuid": uuid, "row": row})
                         extracted = True
                         break 

            count += 1
            
    print(f"Loaded {count} entries from EREPO. Indexed {len(coord_map)} coordinates.")
    return coord_map

def parse_bias(coord_map):
    """Parses BIAS TSV and matches against EREPO map"""
    print("Parsing BIAS data...")
    matched = []
    unmatched = 0
    
    with open(BIAS_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            chrom = row['chromosome']
            if not chrom.startswith('chr'):
                chrom = 'chr' + chrom
            
            try:
                pos = int(row['position'])
            except ValueError:
                continue

            ref = row['refAllele']
            alt = row['altAllele']
            
            key = (chrom, pos, ref, alt)
            entries = coord_map.get(key)
            
            if not entries:
                key_complex = (chrom, pos, "COMPLEX", "COMPLEX")
                entries = coord_map.get(key_complex)
            
            if entries:
                seen = set()
                for e in entries:
                    if e['uuid'] not in seen:
                        # Extract parsed fields
                        erepo = e['row']
                        
                        # Handle HGVS list - split by comma and strip quotes if any
                        hgvs_raw = erepo.get('HGVS Expressions', '')
                        hgvs_list = [x.strip() for x in hgvs_raw.split(',') if x.strip()]
                        
                        # Handle Criteria lists
                        cm_raw = erepo.get('Applied Evidence Codes (Met)', '')
                        criteria_met = [x.strip() for x in cm_raw.split(',') if x.strip()]
                        
                        bias_class = row['acmgClassification']
                        # map basic keys for BIAS
                        if bias_class == "pathogenic": bias_class = "Pathogenic"
                        elif bias_class == "likely_pathogenic": bias_class = "Likely Pathogenic"
                        elif bias_class == "benign": bias_class = "Benign"
                        elif bias_class == "likely_benign": bias_class = "Likely Benign"
                        elif bias_class == "uncertain": bias_class = "Uncertain Significance"
                        else: bias_class = bias_class.capitalize()

                        bias_crit = parse_bias_rationale(row.get('rationale', '{}'))
                        
                        item_obj = {
                            "id": e['uuid'],
                            "variation": erepo.get('Variation', ''),
                            "clinvar_id": erepo.get('ClinVar Variation Id', ''),
                            "hgvs_expressions": hgvs_list,
                            "gene_symbol": erepo.get('HGNC Gene Symbol', ''),
                            "disease": erepo.get('Disease', ''),
                            "mode_of_inheritance": erepo.get('Mode of Inheritance', ''),
                            "classification": erepo.get('Assertion', ''),
                            "criteria_met": criteria_met,
                            "expert_panel": erepo.get('Expert Panel', ''),
                            "intervar_classification": "Uncertain Significance", # Default, populated later
                            "intervar_criteria": [],
                            "bias_classification": bias_class,
                            "bias_criteria": bias_crit,
                            "variant_key": f"{chrom}:{pos}:{ref}:{alt}",
                            "variation_original": erepo.get('Variation', '')
                        }
                        
                        matched.append(item_obj)
                        seen.add(e['uuid'])
            else:
                unmatched += 1
                
    print(f"Matched {len(matched)} BIAS entries. Unmatched: {unmatched}")
    return matched

def parse_intervar(matched_data):
    """Parses InterVar and merges into existing matched data."""
    print("Parsing InterVar data...")
    
    # Create lookup for our current matched data
    # Use variant_key based match if possible? Or (chrom, pos)
    
    lookup = {}
    for i, item in enumerate(matched_data):
        # parse key from variant_key
        parts = item['variant_key'].split(':')
        c, p = parts[0], int(parts[1])
        k = (c, p)
        if k not in lookup: lookup[k] = []
        lookup[k].append(i)
        
    matched_count = 0
    intervar_key = None
    
    with open(INTERVAR_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(filter(lambda x: not x.startswith('##'), f), delimiter='\t')
        
        for row in reader:
            if intervar_key is None:
                for k in row.keys():
                    if k and "InterVar: InterVar and Evidence" in k:
                        intervar_key = k
                        break
            
            if not intervar_key: continue

            chrom = row.get('#Chr') or row.get('Chr')
            if not chrom: continue
            
            if not chrom.startswith('chr'):
                chrom = 'chr' + chrom
                
            try:
                start = int(row['Start'])
            except ValueError:
                continue
                
            pred_string = row.get(intervar_key, '')
            if not pred_string: continue
            
            iv_class, iv_crit = parse_intervar_string(pred_string)
            
            key = (chrom, start)
            indices = lookup.get(key)
            if indices:
                for idx in indices:
                    # Update without overwriting other fields
                    matched_data[idx]['intervar_classification'] = iv_class
                    matched_data[idx]['intervar_criteria'] = iv_crit
                    matched_count += 1
    
    print(f"Matched InterVar data to {matched_count} existing entries.")
    return matched_data

def main():
    erepo_map = parse_erepo()
    merged = parse_bias(erepo_map)
    final_data = parse_intervar(merged)
    
    print(f"Writing {len(final_data)} merged records to {OUTPUT_PATH}")
    with open(OUTPUT_PATH, 'w') as f:
        for item in final_data:
            f.write(json.dumps(item) + "\n")

if __name__ == "__main__":
    main()
