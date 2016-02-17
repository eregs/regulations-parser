===========
Quick Start
===========

Here's an example, using CFPB's regulation H.

.. code-block:: bash

  git clone https://github.com/18F/regulations-parser.git
  cd regulations-parser
  pip install -r requirements.txt
  eregs pipeline 12 1008 output_dir

At the end, you will have subdirectories ``regulation``, ``layer``, ``diff``,
and ``notice`` created under the directory named ``output_dir``. These will
mirror the JSON files sent to the API.

Quick Start with Modified Documents
===================================

Here's an example using FEC's regulation 110, showing how documents can be
tweaked to pass the parser.

.. code-block:: bash

  git clone https://github.com/18F/regulations-parser.git
  cd regulations-parser
  git clone https://github.com/micahsaul/fec_docs
  pip install -r requirements.txt
  echo "LOCAL_XML_PATHS = ['fec_docs']" >> local_settings.py
  eregs pipeline 11 110 output_dir

If you review the history of the ``fec_docs`` repo, you'll see some of the
types of changes that need to be made.
