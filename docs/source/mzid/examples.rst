Usage Examples
--------------

Writing mzIdentML
=================

In this example, we'll walk through the steps involved in writing an mzIdentML file from
some fictional search engine that we have a tabular file for and some information about
search parameters.


.. code-block:: python

    from psims.mzid import MzIdentMLWriter

To begin, you create the writer with a file path, or a previously created file-like object:

.. code-block:: python

    writer = MzIdentMLWriter("path/to/write.mzid")


The following step is identical to the mzML example. Before any content can be written out, the writer must start the document, which can be done by either
using it as a context manager, or by calling it's :meth:`~.MzIdentMLWriter.begin` method.

.. code-block:: python

    with writer:
        writer.controlled_vocabularies()
        ...

The above example uses the context manager syntax, and immediately writes the controlled vocabulary
list to the document. This starts the standard-compliance state-machine, which checks to make sure that
a document proceeds through each section in the expected order, without skipping required sections. The
remainder of these code samples will take place within this context manager.

The next step involves registering the provenance of the document, naming the software(s) that
generated the content and optionally the person and/or organization that was responsible for executing
that software (or the analysis). We can specify the software either using :class:`dict` objects or
directly instantiate :class:`~psims.mzid.components.AnalysisSoftware` instances (pass a :class:`list`
to register multiple software tools).

.. code-block:: python

    software = {
        "name": "my search tool", # Dynamically translated into a cvParam if the name maps to a
                                  # a term in the PSI-MS controlled vocabulary, otherwise
                                  # into `MS:1000799` with the name as the value.
        "id": 1, # If you have only one analysis software, you may omit this
        "version": "v0.1.0",
        "uri": "https://my.tool.site/",
    }
    writer.provenance(software=software)

Before we begin writing the actual information content of the file, we may need to do a bit of
preparation first. The mzIdentML schema involves making references to entites that are by definition
written later than they are referenced, but :mod:`psims` does not like to reference things it doesn't
yet know about. :meth:`~MzIdentMLWriter.register` can be used to pre-declare any type of entity so
:mod:`psims` knows about it before it is used. Alternatively, you can simply ignore the warning
messages :mod:`psims` generates when you reference an unknown identifier. Alternatively, you may
use :meth:`~.ReprBorrowingPartial.register` when accessing a component type as an attribute on an
instance of :class:`~MzIdentMLWriter`, e.g. ``writer.SpectraData.register(1)``.

.. note::
    Registered identifiers should be unique strings and not integers as they do not go
    through the normal identifier conversion process!

The next step is to write the sequence collection by opening the :meth:`~.MzIdentMLWriter.sequence_collection`
context manager and begin writing database sequences. We'll assume that we searched a FASTA database
stored in ``"search_database.fasta"`` with UniProt deflines and that peptides are connected to their
protein via their accession number (``protein.description['id']``).

.. code-block:: python

        from pyteomics import fasta, proforma

        writer.SearchDatabase.register("search_db_1")

        with writer.sequence_collection():
            for protein in fasta.UniProt("search_database.fasta"):
                writer.write_db_sequence(
                    protein.description['id'],
                    protein.sequence,
                    id=protein.description['id'],
                    name=protein.description['entry'],
                    search_database_id="search_db_1",
                    params=[{"protein description": "{entry} {name}".format(**protein.description)}])
            ...

We'll next generate the peptide list. We assume that the peptide spectrum matches are stored in ``"peptides.csv"``
and that the sequences are represented with ``ProForma 2`` notation.

.. code-block:: python

    import csv
    import os

    with open("peptides.csv", 'rt') as peptide_fh:
        peptides_seen = dict()
        for psm in csv.DictReader(peptide_fh):
            peptide_seq = psm['peptide']
            protein_acc = psm['protein']

            key = f"{protein_acc}_$_{peptide_seq}"
            if key in peptides_seen:
                continue
            peptides_seen[key] = (psm['peptide_start'], psm['peptide_end'])

            peptide_seq = proforma.Proforma.parse(peptide_seq)
            unmodified_seq = ''.join([pos[0] for pos in peptide_seq])
            modifications = []
            for i, (aa, mods) in enumerate(peptide_seq, 1):
                for mod in mods:
                    if mod.type in (proforma.TagTypeEnum.generic, proforma.TagTypeEnum.unimod):
                        modifications.append({
                            "location": i,
                            "name": mod.name,
                            "monoisotopic_mass_delta": mod.mass,
                        })
                    else:
                        print(f"... Skipping tag {mod}, don't know how to convert to UNIMOD modification")
            writer.write_peptide(
                unmodified_seq,
                key,
                modifications)
    ...

After the peptides are written, we must write out the ``<PeptideEvidence />``.

.. code-block:: python

    for peptide_key, (peptide_start, peptide_end) in peptides_seen.items():
        protein_id = peptide_key.split("_$_")[0]

        writer.write_peptide_evidence(
            peptide_key,
            protein_id,
            id=f"{peptide_key}_EVIDENCE",
            start_position=peptide_start,
            end_position=peptide_end)
    ...

Now, we can begin to define the analysis workflow used. Let's imagine our search engine
searched three MGF files, with identifiers ``mgf_1`` - ``mgf_3`` which we'll pre-register now.
We open the ``<AnalysisCollection>`` element and declare a single ``<SpectrumIdentification>``
workflow using those MGF files and the search database we registered earlier. We'll also
pre-declare the spectrum identification list ``spectrum_identified_list1`` where we'll
write the identified spectra, and that the workflow took its parameters from
a to-be-defined list of parameters in ``spectrum_idification_params_1``.

.. code-block:: python

    writer.SpectraData.register("mgf_1")
    writer.SpectraData.register("mgf_2")
    writer.SpectraData.register("mgf_3")

    writer.SpectrumIdentificationList.register('spectra_identified_list_1')
    writer.SpectrumIdentificationProtocol.register('spectrum_identification_params_1')

    with writer.analysis_collection():
        writer.SpectrumIdentification(spectra_data_ids_used=[
            "mgf_1", "mgf_2", "mgf_3"
        ], search_database_ids_used=[
            "search_db_1"
        ], spectrum_identification_list_id='spectra_identified_list_1',
        spectrum_identification_protocol_id='spectrum_identification_params_1').write()

Next, we'll actually declare those parameters. The :meth:`~.MzIdentMLWriter.spectrum_identification_protocol`
method is a wrapper for writing ``<SpectrumIdentificationProtocol>`` that does some extra work to
interpret parameters for you. Here is where we list things like mass tolerances, search modification
rules, and any other options that your search engine has that you want to share with the reader.

We'll say we searched our database using trypsin cleavage rules and a constant or "fixed" modification of
"Carbamidomethyl" on all cysteines as is common in shotgun proteomics, but for some bizarre reason we chose
to also consider a variable "Deamidation" on any asparagines. We could also specify these modifications by
their UNIMOD accession numbers, or define custom rules here as well.

The ``parent_tolerance`` and ``fragment_tolerance`` list the mass accuracy error tolerances for
MS1 and MSn spectra respectively, using symmetric upper and lower bounds, but different units (parts-per-million
vs. Da). We'll also specify that we considered monoisotopic masses in the ``additional_search_params``
list, along with a custom parameter "frobnication level", to indicate that we tuned the results
"very carefully".

.. code-block:: python

    with writer.analysis_protocol_collection():
        writer.spectrum_identification_protocol(
            enzymes=[{'missed_cleavages': 1, 'name': 'trypsin', 'id': 1}],
            modification_params=[
                        {'fixed': True,
                         'mass_delta': 57.021465,
                         'params': ['Carbamidomethyl'],
                         'residues': ['C']},
                        {'fixed': False,
                         'mass_delta': 0.984,
                         'params': ['Deamidation'],
                         'residues': ['N']}
            ],
            parent_tolerance=(10, 10, "parts per million"),
            fragment_tolerance=(0.02, 0.02, "dalton"),
            additional_search_params=[
                "parent mass type mono",
                "fragment mass type mono",
                {"frobnication level": "high"} # a custom paramater that will map to a userparam
            ],
            id="spectrum_identification_params_1"
        )
    ...


We're nearly done. The next thing to do is to actually point to the local files that we searched,
namely the sequence database file, the source file for these results, and the spectra data files.

.. code-block:: python

    with writer.data_collection():
        source_file = {
            'file_format': 'tab delimited text format',
            'id': 1,
            'location': f"file://{os.path.realpath('peptides.csv')}"
        }

        search_database = {
            'file_format': 'fasta format',
            'id': 'search_db_1',
            'location': f'file://{os.path.realpath("search_database.fasta")}',
            'name': 'Uniprot Proteins'}

        spectra_data = []
        spectra_data = [{'file_format': 'Mascot MGF format',
                'id': f'mgf_{i}',
                'location': f"file://{os.path.realpath('data' + str(i) + '.mgf')}",
                'spectrum_id_format': 'multiple peak list nativeID format'} for i in range(1, 4)
        ]

        writer.inputs(
            source_file, search_database, spectra_data
        )

        ...

Finally, we can write out those peptide spectrum matches we wanted to report!. Now, we can exploit some
of those mappings and string encoding rules we used earlier to connect PSMs back to their peptides and
their proteins.

We'll read back through our ``"peptides.csv"`` file and reconstruct the peptide ID as we defined it earlier,
and use a few *convenient* columns to fill in spectrum match properties. If we were using a search engine with
one or more registered ``score`` terms, we can specify them here as `params` of the spectrum
identification items. Since we're using an imaginary one, we can use `userParam` "imagine-raw-score" for our
score statistic, and then use generic, a search engine agnostic term for our FDR q-value statistic.

.. code-block:: python

    data_file_to_id = {os.path.realpath('data' + str(i) + '.mgf'): f"mgf_{i}"
                       for i in range(1, 4)}

    with writer.analysis_data():
        with writer.spectrum_identification_list(id='spec_id_list_1'):
            with open("peptides.csv", 'rt') as peptide_fh:
                for i, psm in enumerate(csv.DictReader(peptide_fh)):
                    peptide_seq = psm['peptide']
                    protein_acc = psm['protein']
                    scan_id = psm['scan_id']
                    source_file = psm['ms_data_file']
                    peptide_id = f"{protein_acc}_$_{peptide_seq}"

                    with writer.spectrum_identification_result(
                            spectrum_id=scan_id,
                            id=f'SIR_{i}',
                            spectra_data_id=data_file_to_id[source_file]):

                        writer.write_spectrum_identification_item(
                            calculated_mass_to_charge=psm['theoretical_mz'],
                            charge_state=psm['precursor_charge'],
                            experimental_mass_to_charge=psm['precursor_mz'],
                            id=f'SII_{i}',
                            peptide_id=peptide_id,
                            peptide_evidence_id=f'{peptide_id}_EVIDENCE',
                            params=[
                                {
                                    "imagine-raw-score": psm['raw-score'],
                                },
                                {
                                    "PSM-level q-value": psm['q-value'],
                                }
                            ]
                        )

And with that, we're done! let all the context managers close and the file will
be written and closed correctly.
