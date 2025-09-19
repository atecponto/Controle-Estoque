import sys
import os

# Adiciona o path CORRETO - sobe um nível e entra na pasta controle_estoque
current_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.join(current_dir, 'controle_estoque')
sys.path.append(project_dir)

# Configura o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_estoque.settings')

# Importa a application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# ADICIONE ESTA LINHA ↓↓↓
app = application  # ← Esta linha está FALTANDO!