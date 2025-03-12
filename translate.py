import json
import os
import re
import signal
import sys

import langid
from dotenv import load_dotenv
from google import genai

# Tenta importar o Groq como fallback
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    
def clear_screen():
    """Limpa a tela do terminal."""
    os.system('cls' if os.name == 'nt' else 'clear')
    
def print_header(title):
    """Imprime um cabeçalho formatado."""
    clear_screen()
    print("\n" + "=" * 60)
    print(f"{title:^60}")
    print("=" * 60 + "\n")

def create_env_file_if_needed():
    """Verifica se o arquivo .env existe e, se não, solicita as chaves API ao usuário."""
    if not os.path.exists('.env'):
        print_header("CONFIGURAÇÃO INICIAL")
        print("Arquivo .env não encontrado. Vamos criar um agora.")
        print("\nVocê precisará fornecer pelo menos uma das seguintes chaves API:")
        
        print("\n1. Google Gemini API Key")
        print("   Obtenha em: https://ai.google.dev/gemini-api/docs/api-key?hl=pt-br")
        gemini_key = input("\nDigite sua chave API do Google Gemini (pressione Enter para pular): ").strip()
        
        print("\n2. Groq API Key (opcional, usado como fallback)")
        print("   Obtenha em: https://console.groq.com/keys")
        groq_key = input("\nDigite sua chave API do Groq (pressione Enter para pular): ").strip()
        
        if not gemini_key and not groq_key:
            print("\nErro: Pelo menos uma chave API é necessária para o funcionamento do aplicativo.")
            sys.exit(1)
            
        # Cria o arquivo .env
        with open('.env', 'w', encoding='utf-8') as env_file:
            if gemini_key:
                env_file.write(f"GEMINI_API_KEY={gemini_key}\n")
            if groq_key:
                env_file.write(f"GROQ_API_KEY={groq_key}\n")
                
        print("\nArquivo .env criado com sucesso!")
        input("Pressione Enter para continuar...")

# Chama a função para verificar o .env antes de carregar as variáveis de ambiente
create_env_file_if_needed()

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configura a API do Google Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Erro: GEMINI_API_KEY não encontrada. Crie um arquivo .env com sua chave GEMINI_API_KEY.")
    sys.exit(1)

# Configura a API do Groq como fallback
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY and GROQ_AVAILABLE:
    print("Aviso: GROQ_API_KEY não encontrada. Não será possível usar o fallback para o Groq.")

# Inicializa o cliente Gemini
client = genai.Client(api_key=API_KEY)

# Inicializa o cliente Groq se disponível
groq_client = None
if GROQ_AVAILABLE and GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

# Configura o handler para CTRL+C
def signal_handler(sig, frame):
    print("\n\nOperação cancelada pelo usuário. As traduções já aprovadas foram salvas.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


def list_directory_contents(current_dir):
    """Lista os arquivos e diretórios no diretório atual."""
    try:
        items = os.listdir(current_dir)
        # Separar diretórios e arquivos
        directories = [item for item in items if os.path.isdir(os.path.join(current_dir, item))]
        files = [item for item in items if os.path.isfile(os.path.join(current_dir, item))]
        
        # Ordenar alfabeticamente
        directories.sort()
        files.sort()
        
        return directories, files
    except Exception as e:
        print(f"Erro ao listar o diretório: {e}")
        return [], []

def select_file_interactively():
    """Interface interativa por linha de comando para selecionar um arquivo."""
    # Começa no diretório atual
    current_dir = os.getcwd()
    
    while True:
        print_header("SELEÇÃO DE ARQUIVO")
        print(f"Diretório atual: {current_dir}")
        print("-" * 60)
        
        directories, files = list_directory_contents(current_dir)
        
        # Lista de todas as opções
        options = []
        
        # Adiciona opção para subir um nível se não estiver na raiz
        if current_dir != os.path.dirname(current_dir):
            print("[0] .. (Voltar para o diretório anterior)")
            options.append(("parent", None))
        
        # Lista diretórios
        for i, directory in enumerate(directories, 1):
            print(f"[{i}] 📁 {directory}/")
            options.append(("dir", directory))
        
        # Lista arquivos
        for i, file in enumerate(files, len(directories) + 1):
            print(f"[{i}] 📄 {file}")
            options.append(("file", file))
        
        # Solicita a escolha do usuário
        print("\n(Digite q para sair)")
        choice = input("Digite o número da opção desejada: ")
        
        if choice.lower() == 'q':
            print("\nOperação cancelada pelo usuário.")
            sys.exit(0)
        
        try:
            choice = int(choice)
            
            if 0 <= choice < len(options):
                option_type, option_value = options[choice]
                
                if option_type == "parent":
                    current_dir = os.path.dirname(current_dir)
                elif option_type == "dir":
                    current_dir = os.path.join(current_dir, option_value)
                elif option_type == "file":
                    return os.path.join(current_dir, option_value)
            else:
                input("Opção inválida. Pressione Enter para continuar...")
        
        except ValueError:
            input("Por favor, digite um número válido. Pressione Enter para continuar...")
        except Exception as e:
            input(f"Erro: {e}. Pressione Enter para continuar...")

def read_file(filename):
    """Lê o arquivo e retorna seu conteúdo."""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Erro: Arquivo '{filename}' não encontrado.")
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao ler o arquivo: {e}")
        sys.exit(1)

def save_file(filename, content):
    """Salva o conteúdo em um arquivo."""
    backup_filename = filename + '.bak'
    try:
        # Cria um backup do arquivo original se ele ainda não existir
        if not os.path.exists(backup_filename):
            with open(filename, 'r', encoding='utf-8') as original:
                with open(backup_filename, 'w', encoding='utf-8') as backup:
                    backup.write(original.read())
            print(f"Backup criado como '{backup_filename}'")
        
        # Salva o novo conteúdo
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Arquivo salvo com sucesso!")
        input("Pressione Enter para continuar...")
    except Exception as e:
        print(f"Erro ao salvar o arquivo: {e}")
        input("Pressione Enter para continuar...")

def parse_records(content):
    """Extrai os registros do conteúdo do arquivo usando expressões regulares."""
    pattern = r'\{\s*([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
    matches = re.finditer(pattern, content)
    
    records = []
    positions = []
    raw_records = []
    
    for match in matches:
        record_text = match.group(0)
        start_pos = match.start()
        end_pos = match.end()
        
        # Armazena o texto bruto do registro
        raw_records.append(record_text)
        
        # Converte o texto do registro para um dicionário
        record_dict = {}
        try:
            lines = record_text.strip('{}').split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('//'):  # Ignora linhas vazias e comentários
                    if ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            key, value = parts
                            key = key.strip()
                            value = value.strip()
                            record_dict[key] = value
        except Exception as e:
            print(f"Erro ao processar registro: {e}")
            print(f"Texto do registro: {record_text}")
            continue
        
        records.append(record_dict)
        positions.append((start_pos, end_pos))
    
    return records, positions, content, raw_records

def is_portuguese(text):
    """Verifica se o texto já está em português."""
    try:
        # O langid pode falhar em textos muito curtos ou que contêm muitas palavras estrangeiras
        lang, confidence = langid.classify(text)
        
        # Retorna True se for português (pt) com uma confiança razoável
        return lang == 'pt' and confidence > 0.5
    except:
        # Em caso de erro, presume que não é português
        return False

def translate_with_gemini(text, field_name, original_text=None, is_retry=False):
    """Traduz o texto usando a API do Google Gemini."""
    if is_retry:
        prompt = f"""
        Traduza o seguinte texto de inglês para português para um jogo indie. A tradução anterior não foi satisfatória.
        
        Campo: {field_name}
        Texto original: {text}
        Tentativa anterior: {original_text}
        
        Mantenha a tradução com tamanho similar ao original e preserve a terminologia de jogos.
        Evite traduções literais que percam o significado ou o humor do original.
        NÃO repita o texto original junto com a tradução!
        
        Obrigatório: Retorne apenas o texto traduzido e nada mais. 
        Não adicione informações extras ou explicações.
        """
    else:
        prompt = f"""
        Traduza o seguinte texto de inglês para português para um jogo indie.
        
        Campo: {field_name}
        Texto original: {text}
        
        Mantenha a tradução com tamanho similar ao original e preserve a terminologia de jogos.
        Evite traduções literais que percam o significado ou o humor do original.
        NÃO repita o texto original junto com a tradução!
        
        Obrigatório: Retorne apenas o texto traduzido e nada mais. 
        Não adicione informações extras ou explicações.
        """
    
    try:
        print("Traduzindo com Google Gemini...")
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text.strip(), True
    except Exception as e:
        print(f"Erro na tradução com Gemini: {e}")
        return None, False

def translate_with_groq(text, field_name, original_text=None, is_retry=False):
    """Traduz o texto usando a API do Groq como fallback."""
    if not GROQ_AVAILABLE or not groq_client:
        return "ERRO NA TRADUÇÃO - Groq não disponível", False
    
    if is_retry:
        prompt = f"""Traduza o seguinte texto de inglês para português para um jogo indie. A tradução anterior não foi satisfatória.
        
Campo: {field_name}
Texto original: {text}
Tentativa anterior: {original_text}
        
Mantenha a tradução com tamanho similar ao original e preserve a terminologia de jogos.
Evite traduções literais que percam o significado ou o humor do original.
NÃO repita o texto original junto com a tradução!

Obrigatório: Retorne apenas o texto traduzido e nada mais. 
Não adicione informações extras ou explicações."""
    else:
        prompt = f"""Traduza o seguinte texto de inglês para português para um jogo indie.
        
Campo: {field_name}
Texto original: {text}
        
Mantenha a tradução com tamanho similar ao original e preserve a terminologia de jogos.
Evite traduções literais que percam o significado ou o humor do original.
NÃO repita o texto original junto com a tradução!

Obrigatório: Retorne apenas o texto traduzido e nada mais. 
Não adicione informações extras ou explicações."""
    
    try:
        print("Traduzindo com Groq (fallback)...")
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama3-70b-8192",
        )
        return chat_completion.choices[0].message.content.strip(), True
    except Exception as e:
        print(f"Erro na tradução com Groq: {e}")
        return "ERRO NA TRADUÇÃO", False

def translate_text(text, field_name, original_text=None, is_retry=False):
    """Traduz o texto usando a API do Google Gemini com fallback para Groq."""
    # Tenta primeiro com Gemini
    result, success = translate_with_gemini(text, field_name, original_text, is_retry)
    
    # Se falhar, tenta com Groq como fallback
    if not success:
        print("Tradução com Gemini falhou. Tentando com Groq como fallback...")
        result, success = translate_with_groq(text, field_name, original_text, is_retry)
    
    return result

def update_content(content, positions, records, raw_records, translated_fields, field_name):
    """Atualiza o conteúdo do arquivo com as traduções aprovadas."""
    # Cria uma cópia do conteúdo original
    new_content = content
    
    # Aplica as traduções de trás para frente para evitar problemas com índices
    for i in range(len(records) - 1, -1, -1):
        if i in translated_fields:
            record = records[i]
            start_pos, end_pos = positions[i]
            raw_record = raw_records[i]
            
            # Extrai a linha com o campo a ser traduzido
            field_pattern = re.compile(r'(\s*' + re.escape(field_name) + r':\s*)([^\n]*)', re.MULTILINE)
            field_match = field_pattern.search(raw_record)
            
            if field_match:
                # Substitui o valor do campo no texto original
                prefix = field_match.group(1)  # field_name + ":"
                translated_value = translated_fields[i]
                
                # Substitui apenas a linha específica no texto do registro
                updated_record = field_pattern.sub(f'{prefix}{translated_value}', raw_record)
                
                # Substitui o registro original pelo atualizado no conteúdo completo
                new_content = new_content[:start_pos] + updated_record + new_content[end_pos:]
    
    return new_content

def select_from_menu(options, title, prompt="Escolha uma opção:"):
    """Exibe um menu e retorna a opção selecionada."""
    while True:
        print_header(title)
        
        for i, option in enumerate(options):
            print(f"[{i+1}] {option}")
        
        print("\n(Digite q para sair)")
        choice = input(f"{prompt} ")
        
        if choice.lower() == 'q':
            return None
        
        try:
            choice = int(choice)
            if 1 <= choice <= len(options):
                return options[choice-1]
            else:
                input("Opção inválida. Pressione Enter para continuar...")
        except ValueError:
            input("Por favor, digite um número válido. Pressione Enter para continuar...")

def select_field_interactively(available_fields):
    """Seleciona um campo para tradução de forma interativa."""
    fields_list = sorted(list(available_fields))
    
    while True:
        print_header("SELEÇÃO DE CAMPO PARA TRADUÇÃO")
        
        for i, field in enumerate(fields_list, 1):
            print(f"[{i}] {field}")
        
        print("\n(Digite q para sair)")
        choice = input("Digite o número do campo que deseja traduzir: ")
        
        if choice.lower() == 'q':
            print("\nOperação cancelada pelo usuário.")
            sys.exit(0)
        
        try:
            choice = int(choice)
            if 1 <= choice <= len(fields_list):
                return fields_list[choice-1]
            else:
                input("Opção inválida. Pressione Enter para continuar...")
        except ValueError:
            input("Por favor, digite um número válido. Pressione Enter para continuar...")

def show_translation_options(history_index, history_length):
    """Exibe as opções para o usuário durante a tradução."""
    print("\nOpções:")
    print("[1] Aprovar esta tradução")
    print("[2] Gerar nova tradução")
    
    if history_index > 0:
        print("[3] Ver tradução anterior")
    
    if history_index < history_length - 1:
        print("[4] Ver próxima tradução")
    
    print("[5] Usar texto original")
    print("[6] Modificar manualmente")
    print("[q] Sair")

def get_translation_choice(history_index, history_length):
    """Obtém a escolha do usuário para a tradução atual."""
    show_translation_options(history_index, history_length)
    
    while True:
        choice = input("\nEscolha uma opção: ").lower()
        
        if choice == 'q':
            return 'quit'
        
        try:
            choice = int(choice)
            if choice == 1:
                return 'approve'
            elif choice == 2:
                return 'new'
            elif choice == 3 and history_index > 0:
                return 'previous'
            elif choice == 4 and history_index < history_length - 1:
                return 'next'
            elif choice == 5:
                return 'original'
            elif choice == 6:
                return 'manual'
            else:
                print("Opção inválida. Tente novamente.")
        except ValueError:
            print("Por favor, digite um número válido.")

def main():
    """Função principal do script."""
    try:
        # Banner inicial
        print_header("TRADUTOR DE JOGOS INDIE")
        input("Pressione Enter para selecionar um arquivo...")
        
        # Seleciona o arquivo
        filename = select_file_interactively()
        if not filename:
            print("Nenhum arquivo selecionado. Encerrando.")
            sys.exit(0)
        
        print_header("PROCESSANDO ARQUIVO")
        print(f"Arquivo selecionado: {filename}")
        
        # Lê o conteúdo do arquivo
        content = read_file(filename)
        
        # Extrai os registros do conteúdo
        records, positions, content, raw_records = parse_records(content)
        
        print(f"Foram encontrados {len(records)} registros no arquivo.")
        input("Pressione Enter para continuar...")
        
        # Obtém os campos disponíveis para tradução
        if not records:
            print("Nenhum registro encontrado no arquivo. Encerrando.")
            sys.exit(1)
        
        available_fields = set()
        for record in records:
            available_fields.update(record.keys())
        
        # Seleciona o campo para tradução
        field_name = select_field_interactively(available_fields)
        
        # Dicionário para armazenar as traduções aprovadas
        translated_fields = {}
        
        # Conteúdo atualizado que será salvo a cada aprovação
        current_content = content
        
        # Processa cada registro
        for i, record in enumerate(records):
            if field_name in record:
                print_header(f"TRADUÇÃO DE REGISTRO {i+1}/{len(records)}")
                print(f"Nome: {record.get('name', record.get('devname', 'N/A'))}")
                
                original_text = record[field_name]
                print(f"\nOriginal ({field_name}):\n{original_text}")
                
                # Verifica se o texto já está em português
                if is_portuguese(original_text):
                    print("\nTexto já está em português. Pulando para o próximo registro...")
                    input("Pressione Enter para continuar...")
                    continue
                
                # Traduz o texto
                print("\nGerando tradução inicial...")
                translated_text = translate_text(original_text, field_name)
                
                # Histórico de traduções para este registro
                translation_history = [translated_text]
                history_index = 0
                
                # Loop até que a tradução seja aprovada
                is_approved = False
                while not is_approved:
                    print_header(f"TRADUÇÃO DE REGISTRO {i+1}/{len(records)}")
                    print(f"Nome: {record.get('name', record.get('devname', 'N/A'))}")
                    print(f"\nOriginal ({field_name}):\n{original_text}")
                    
                    current_translation = translation_history[history_index]
                    print(f"\nTradução ({history_index + 1}/{len(translation_history)}):\n{current_translation}")
                    
                    # Obtém a escolha do usuário
                    choice = get_translation_choice(history_index, len(translation_history))
                    
                    if choice == 'approve':
                        # Aprova a tradução atual
                        translated_fields[i] = current_translation
                        is_approved = True
                        
                        # Atualiza o conteúdo do arquivo em tempo real
                        current_content = update_content(current_content, positions, records, raw_records, {i: current_translation}, field_name)
                        save_file(filename, current_content)
                        print(f"Tradução aplicada ao arquivo em tempo real.")
                    
                    elif choice == 'new':
                        # Gera uma nova tradução
                        print("\nGerando nova tradução...")
                        new_translation = translate_text(original_text, field_name, current_translation, is_retry=True)
                        translation_history.append(new_translation)
                        history_index = len(translation_history) - 1
                    
                    elif choice == 'previous':
                        # Vai para a tradução anterior no histórico
                        history_index -= 1
                    
                    elif choice == 'next':
                        # Vai para a próxima tradução no histórico
                        history_index += 1
                    
                    elif choice == 'original':
                        # Usa o texto original (sem tradução)
                        translated_fields[i] = original_text
                        is_approved = True
                        
                        # Atualiza o conteúdo do arquivo em tempo real
                        current_content = update_content(current_content, positions, records, raw_records, {i: original_text}, field_name)
                        save_file(filename, current_content)
                        print(f"Texto original mantido e aplicado ao arquivo.")
                    
                    elif choice == 'manual':
                        # Permite modificação manual
                        print("\nDigite a tradução manualmente:")
                        manual_translation = input("> ")
                        translation_history.append(manual_translation)
                        history_index = len(translation_history) - 1
                    
                    elif choice == 'quit':
                        # Sai do programa
                        print("\nOperação cancelada pelo usuário.")
                        sys.exit(0)
        
        print_header("CONCLUSÃO")
        print("Processo de tradução concluído com sucesso!")
        input("Pressione Enter para sair...")
    
    except KeyboardInterrupt:
        print("\n\nOperação cancelada pelo usuário. As traduções já aprovadas foram salvas.")
        sys.exit(0)

if __name__ == "__main__":
    main()