# Table/Figure/Caption Text-Layer Coverage Audit

## Scope

This audit sampled existing PDFs and inspected only the machine-readable text layer. It does not modify the main system, rebuild the index, alter frozen results, or perform layout-aware table extraction or image interpretation.

## Sample Strategy

The sample prioritized returned/sample-return papers, meteorite organic compound papers, analytical-methods and contamination-control papers, and documents whose text layer contains Table/Fig/Figure/caption-like markers.

## Aggregate Counts

| metric | value |
| --- | --- |
| sampled_documents | 20 |
| documents_with_table_markers | 18 |
| documents_with_figure_markers | 20 |
| documents_with_caption_text | 20 |
| documents_with_table_like_text | 19 |
| documents_with_surrounding_refs | 14 |
| cases_not_recoverable_from_text_layer | 0 |

## Per-Document Flags

| sample_id | filename | table_markers | figure_markers | caption_text | table_like_text | possible_not_recoverable |
| --- | --- | --- | --- | --- | --- | --- |
| TFCA001 | Investigating the impact of xray computed tomography imaging... | 1 | 1 | 1 | 1 | 0 |
| TFCA002 | PAHs, hydrocarbons, and dimethylsulfides in Asteroid Ryugu s... | 1 | 1 | 1 | 1 | 0 |
| TFCA003 | Amino acids on witness coupons collected from the ISASJAXA c... | 1 | 1 | 1 | 1 | 0 |
| TFCA004 | The Winchcombe meteorite, a unique and pristine witness from... | 0 | 1 | 1 | 1 | 0 |
| TFCA005 | Quantitative Analysis of Meteorite Elements Based on the Mul... | 1 | 1 | 1 | 1 | 0 |
| TFCA006 | Concerns of Organic Contamination for Sample Return Space Mi... | 1 | 1 | 1 | 1 | 0 |
| TFCA007 | Cold curation of pristine astromaterials- Insights from the ... | 1 | 1 | 1 | 1 | 0 |
| TFCA008 | A contamination assessment of the CI carbonaceous meteorite ... | 1 | 1 | 1 | 1 | 0 |
| TFCA009 | Molecular distribution and 13C isotope composition of volati... | 1 | 1 | 1 | 1 | 0 |
| TFCA010 | Infrared imaging spectroscopy with micron resolution of Sutt... | 1 | 1 | 1 | 1 | 0 |
| TFCA011 | Organic Matter Detection on Mars by Pyrolysis-FTIR- An Analy... | 1 | 1 | 1 | 1 | 0 |
| TFCA012 | Raman spectroscopic characterization of a highly weathered b... | 0 | 1 | 1 | 1 | 0 |
| TFCA013 | Reflectance spectroscopy of organic compounds- 1. Alkanes.pd... | 1 | 1 | 1 | 0 | 0 |
| TFCA014 | Nanoscale mineralogy and organic structure in Orgueil (CI) a... | 1 | 1 | 1 | 1 | 0 |
| TFCA015 | Abiotic formation of alkylsulfonic acids in interstellar ana... | 1 | 1 | 1 | 1 | 0 |
| TFCA016 | Motion of dust ejected from the surface of asteroid (101955)... | 1 | 1 | 1 | 1 | 0 |
| TFCA017 | Indigenous OrganicOxidized Fluid Interactions in the Tissint... | 1 | 1 | 1 | 1 | 0 |
| TFCA018 | 10.1016_j.gca.2018.01.038.pdf | 1 | 1 | 1 | 1 | 0 |
| TFCA019 | Fast online deconvolution of calcium imaging data.pdf | 1 | 1 | 1 | 1 | 0 |
| TFCA020 | Fortenberry, R.C. Spectroscopic Constants and Anharmonic Vib... | 1 | 1 | 1 | 1 | 0 |

## Interpretation

The current workflow can retrieve and cite table, figure, and caption evidence when those elements survive in the PDF text layer. In this audit, many sampled documents retained caption-like text and row-like numeric/text fragments that could be indexed as ordinary text evidence.

However, this is not equivalent to layout-aware table extraction or figure interpretation. Flattened text can lose two-dimensional table structure, row-column alignment, symbols, units, panel labels, and relationships between a figure and surrounding caption/body text. Cases flagged as not recoverable are cases where references or markers were visible but the corresponding caption/row-like content was incomplete or absent in the text layer.
