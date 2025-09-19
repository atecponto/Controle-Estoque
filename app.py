import sys
import os

# Adiciona o path do projeto ao Python
sys.path.append(os.path.join(os.path.dirname(__file__), 'controle_estoque'))

from controle_estoque.wsgi import application

app = application