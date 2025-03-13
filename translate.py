import os
import re
import signal
import sys
import time

import langid
from dotenv import load_dotenv
from google import genai

# Tenta importar o Groq como fallback
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

gemini_last_error_time = 0
gemini_cooldown_period = 60


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
        directories = [item for item in items if os.path.isdir(os.path.join(current_dir, item))]
        files = [item for item in items if os.path.isfile(os.path.join(current_dir, item))]
        directories.sort()
        files.sort()
        return directories, files
    except Exception as e:
        print(f"Erro ao listar o diretório: {e}")
        return [], []


def select_file_interactively():
    """Interface interativa por linha de comando para selecionar um arquivo."""
    current_dir = os.getcwd()
    
    while True:
        print_header("SELEÇÃO DE ARQUIVO")
        print(f"Diretório atual: {current_dir}")
        print("-" * 60)
        
        directories, files = list_directory_contents(current_dir)
        options = []
        
        if current_dir != os.path.dirname(current_dir):
            print("[0] .. (Voltar para o diretório anterior)")
            options.append(("parent", None))
        
        for i, directory in enumerate(directories, 1):
            print(f"[{i}] 📁 {directory}/")
            options.append(("dir", directory))
        
        for i, file in enumerate(files, len(directories) + 1):
            print(f"[{i}] 📄 {file}")
            options.append(("file", file))
        
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
    """Salva o conteúdo em um arquivo, preservando a formatação exata."""
    backup_filename = filename + '.bak'
    try:
        if not os.path.exists(backup_filename):
            with open(filename, 'r', encoding='utf-8') as original:
                with open(backup_filename, 'w', encoding='utf-8', newline='') as backup:
                    backup.write(original.read())
            print(f"Backup criado como '{backup_filename}'")
        
        with open(filename, 'w', encoding='utf-8', newline='') as file:
            file.write(content)
        print(f"Arquivo salvo com sucesso!")
        input("Pressione Enter para continuar...")
    except Exception as e:
        print(f"Erro ao salvar o arquivo: {e}")
        input("Pressione Enter para continuar...")


def parse_record_fields(block_text):
    """
    Extrai os campos de um bloco mantendo a formatação original.
    Ignora linhas que começam com '//' (comentários).
    """
    record_dict = {}
    inner = block_text.strip()[1:-1]
    lines = inner.splitlines()
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("//"):
            continue
        if ':' in stripped_line:
            key, value = stripped_line.split(":", 1)
            key = key.strip().strip('"').strip("'")
            value = value.strip().rstrip(',')
            record_dict[key] = value
    return record_dict


def parse_records_fixed(content):
    """
    Nova lógica para extrair registros do conteúdo,
    preservando todo o layout original.
    Utiliza regex para capturar exatamente as seções delimitadas por '{' e '}'.
    Retorna:
      - records: lista de dicionários com os campos extraídos (para referência)
      - positions: lista de tuplas (início, fim) de cada bloco no conteúdo original
      - content: o conteúdo original completo
      - raw_records: lista dos blocos exatamente como foram encontrados
    """
    record_pattern = re.compile(r'\{.*?\}', re.DOTALL)
    records = []
    positions = []
    raw_records = []
    
    for match in record_pattern.finditer(content):
        start, end = match.span()
        block_text = match.group(0)
        raw_records.append(block_text)
        records.append(parse_record_fields(block_text))
        positions.append((start, end))
    
    return records, positions, content, raw_records


def is_portuguese(text):
    """Verifica se o texto já está em português."""
    try:
        lang, confidence = langid.classify(text)
        return lang == 'pt' and confidence > 0.5
    except:
        return False


def translate_with_gemini(record_text, field_name, original_text=None, is_retry=False):
    """
    Traduz apenas o campo específico do bloco de texto usando a API do Google Gemini.
    Envia o bloco inteiro entre chaves para melhor contexto.
    """
    if is_retry:
        prompt = f"""
        Traduza apenas o campo '{field_name}' no seguinte bloco JSON de um jogo indie.
        A tradução anterior não foi satisfatória.
        
        Bloco original:
        ```
        {record_text}
        ```
        
        INSTRUÇÕES IMPORTANTES:
        1. Traduza SOMENTE o valor para o campo '{field_name}' do inglês para o português.
        2. NÃO altere nenhum outro campo ou texto.
        3. NÃO altere formatação, espaços, quebras de linha ou indentação.
        4. Mantenha todas as aspas, vírgulas e pontuação exatamente como no original.
        5. Retorne o bloco COMPLETO, incluindo todos os campos.
        
        Exemplo:
        Se o campo 'name' com valor "Bee in car" deve ser traduzido, apenas substitua "Bee in car" por "Abelha no carro", mantendo todo o resto idêntico.
        """
    else:
        prompt = f"""
        Traduza apenas o campo '{field_name}' no seguinte bloco JSON de um jogo indie.
        
        Bloco original:
        ```
        {record_text}
        ```
        
        Traduza APENAS o valor do campo '{field_name}' do inglês para o português.
        Mantenha todos os outros campos EXATAMENTE iguais.
        Mantenha todos os espaços, aspas, vírgulas e outros caracteres como estão.
        
        INSTRUÇÕES IMPORTANTES:
        1. Traduza SOMENTE o valor para o campo '{field_name}' do inglês para o português.
        2. NÃO altere nenhum outro campo ou texto.
        3. NÃO altere formatação, espaços, quebras de linha ou indentação.
        4. Mantenha todas as aspas, vírgulas e pontuação exatamente como no original.
        5. Retorne o bloco COMPLETO, incluindo todos os campos.
        
        Exemplo:
        Se o campo 'name' com valor "Bee in car" deve ser traduzido, apenas substitua "Bee in car" por "Abelha no carro", mantendo todo o resto idêntico.
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
        return str(e), False


def translate_with_groq(record_text, field_name, original_text=None, is_retry=False):
    """
    Traduz apenas o campo específico do bloco de texto usando a API do Groq como fallback.
    Envia o bloco inteiro entre chaves para melhor contexto.
    """
    if not GROQ_AVAILABLE or not groq_client:
        return "ERRO NA TRADUÇÃO - Groq não disponível", False
    
    if is_retry:
        prompt = f"""
        Traduza apenas o campo '{field_name}' no seguinte bloco JSON de um jogo indie.
        A tradução anterior não foi satisfatória.
        
        Bloco original:
        ```
        {record_text}
        ```
        
        INSTRUÇÕES IMPORTANTES:
        1. Traduza SOMENTE o valor para o campo '{field_name}' do inglês para o português.
        2. NÃO altere nenhum outro campo ou texto.
        3. NÃO altere formatação, espaços, quebras de linha ou indentação.
        4. Mantenha todas as aspas, vírgulas e pontuação exatamente como no original.
        5. Retorne o bloco COMPLETO, incluindo todos os campos.
        
        Exemplo:
        Se o campo 'name' com valor "Bee in car" deve ser traduzido, apenas substitua "Bee in car" por "Abelha no carro", mantendo todo o resto idêntico.
        """
    else:
        prompt = f"""
        Traduza apenas o campo '{field_name}' no seguinte bloco JSON de um jogo indie.
        
        Bloco original:
        ```
        {record_text}
        ```
        
        INSTRUÇÕES IMPORTANTES:
        1. Traduza SOMENTE o valor para o campo '{field_name}' do inglês para o português.
        2. NÃO altere nenhum outro campo ou texto.
        3. NÃO altere formatação, espaços, quebras de linha ou indentação.
        4. Mantenha todas as aspas, vírgulas e pontuação exatamente como no original.
        5. Retorne o bloco COMPLETO, incluindo todos os campos.
        
        Exemplo:
        Se o campo 'name' com valor "Bee in car" deve ser traduzido, apenas substitua "Bee in car" por "Abelha no carro", mantendo todo o resto idêntico.
        """
    
    try:
        print("Traduzindo com Groq (fallback)...")
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192",
        )
        return chat_completion.choices[0].message.content.strip(), True
    except Exception as e:
        print(f"Erro na tradução com Groq: {e}")
        return "ERRO NA TRADUÇÃO", False


def extract_field_value(record_text, field_name):
    """
    Extrai o valor de um campo específico de um bloco de texto.
    """
    pattern = re.compile(r'"?' + re.escape(field_name) + r'"?\s*:\s*([^,\n]+)')
    match = pattern.search(record_text)
    if match:
        return match.group(1).strip()
    return None


def translate_text(record_text, field_name, original_text=None, is_retry=False):
    """
    Traduz o texto usando a API do Google Gemini com fallback para Groq.
    Envia todo o bloco de texto e recebe o bloco inteiro com a tradução.
    """
    global gemini_last_error_time
    current_time = time.time()
    use_gemini = True
    field_value = extract_field_value(record_text, field_name)
    if field_value and is_portuguese(field_value):
        return record_text, True
    
    if gemini_last_error_time > 0:
        time_since_error = current_time - gemini_last_error_time
        if time_since_error < gemini_cooldown_period:
            print(f"Gemini em cooldown por mais {gemini_cooldown_period - time_since_error:.0f} segundos. Usando Groq...")
            use_gemini = False
        else:
            print("Período de cooldown do Gemini encerrado. Tentando usar o Gemini novamente...")
            gemini_last_error_time = 0
    
    result = None
    success = False
    if use_gemini:
        result, success = translate_with_gemini(record_text, field_name, original_text, is_retry)
        if not success:
            error_message = str(result) if result else "Erro desconhecido"
            if any(k in error_message.lower() for k in ["quota", "rate limit", "limit exceeded"]):
                gemini_last_error_time = current_time
                print(f"Limite da API Gemini atingido. Cooldown de {gemini_cooldown_period} segundos.")
                print("Alternando automaticamente para Groq...")
            print("Tradução com Gemini falhou. Tentando com Groq como fallback...")
            result, success = translate_with_groq(record_text, field_name, original_text, is_retry)
    else:
        result, success = translate_with_groq(record_text, field_name, original_text, is_retry)
    
    if not success:
        return "ERRO NA TRADUÇÃO - Todas as APIs falharam", False
    
    result = result.replace('```', '').strip()
    return result, success


def update_content_fixed(content, positions, translated_blocks):
    """
    Atualiza o conteúdo original substituindo os blocos pelos traduzidos.
    A substituição é feita de trás para frente para preservar os índices.
    
    translated_blocks: dicionário onde a chave é o índice do registro e o valor
    é o bloco traduzido que deve substituir o bloco original.
    """
    new_content = content
    for i in sorted(translated_blocks.keys(), reverse=True):
        start, end = positions[i]
        new_block = translated_blocks[i]
        new_content = new_content[:start] + new_block + new_content[end:]
    return new_content


def _update_single_record(record_text, field_name, new_value):
    """
    Atualiza apenas o valor de um campo específico no bloco, mantendo a formatação exata.
    """
    lines = record_text.split('\n')
    updated_lines = []
    pattern = re.compile(r'^(\s*"?' + re.escape(field_name) + r'"?\s*:\s*)([^,\n]*)(.*)$')
    
    for line in lines:
        match = pattern.match(line)
        if not match:
            updated_lines.append(line)
            continue
        
        prefix = match.group(1)
        old_value = match.group(2)
        suffix = match.group(3)
        is_quoted = old_value.strip().startswith('"') or old_value.strip().startswith("'")
        quote_type = old_value.strip()[0] if is_quoted else ''
        
        if is_quoted:
            if quote_type == '"':
                escaped_value = new_value.replace('"', '\\"')
            else:
                escaped_value = new_value.replace("'", "\\'")
            new_line = f"{prefix}{quote_type}{escaped_value}{quote_type}{suffix}"
        else:
            new_line = f"{prefix}{new_value}{suffix}"
        
        updated_lines.append(new_line)
    
    return '\n'.join(updated_lines)


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


def extract_field_display_value(record_text, field_name):
    """
    Extrai o valor limpo de um campo para exibição.
    """
    try:
        pattern = re.compile(r'^\s*"?' + re.escape(field_name) + r'"?\s*:\s*([^,\n]+)', re.MULTILINE)
        match = pattern.search(record_text)
        if match:
            value = match.group(1).strip()
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            if value.endswith(','):
                value = value[:-1]
            if '//' in value:
                value = value.split('//')[0].strip()
            value = value.replace('\\"', '"').replace("\\'", "'")
            return value
        return None
    except Exception as e:
        print(f"Erro ao extrair valor do campo: {e}")
        return None


def main():
    """Função principal do script."""
    try:
        print_header("TRADUTOR DE JOGOS INDIE")
        input("Pressione Enter para selecionar um arquivo...")
        filename = select_file_interactively()
        if not filename:
            print("Nenhum arquivo selecionado. Encerrando.")
            sys.exit(0)
        
        print_header("PROCESSANDO ARQUIVO")
        print(f"Arquivo selecionado: {filename}")
        content = read_file(filename)
        
        # Utiliza a nova função de extração que preserva o layout
        records, positions, content, raw_records = parse_records_fixed(content)
        
        print(f"Foram encontrados {len(records)} registros no arquivo.")
        input("Pressione Enter para continuar...")
        
        if not records:
            print("Nenhum registro encontrado no arquivo. Encerrando.")
            sys.exit(1)
        
        available_fields = set()
        for record in records:
            available_fields.update(record.keys())
        
        field_name = select_field_interactively(available_fields)
        translated_blocks = {}
        
        # "content" mantém o conteúdo original para que os índices em "positions" permaneçam válidos
        for i, record in enumerate(records):
            if field_name in record:
                print_header(f"TRADUÇÃO DE REGISTRO {i+1}/{len(records)}")
                print(f"Identificador: {record.get('name', record.get('devname', 'N/A'))}")
                original_block = raw_records[i]
                original_text = extract_field_display_value(original_block, field_name)
                
                if not original_text:
                    print(f"\nCampo '{field_name}' não encontrado ou vazio neste registro. Pulando...")
                    input("Pressione Enter para continuar...")
                    continue
                
                print(f"\nOriginal ({field_name}):\n{original_text}")
                
                if is_portuguese(original_text):
                    print("\nTexto já está em português. Pulando para o próximo registro...")
                    input("Pressione Enter para continuar...")
                    continue
                
                print("\nGerando tradução inicial...")
                translated_block, success = translate_text(original_block, field_name)
                translated_value = extract_field_display_value(translated_block, field_name)
                if translated_value == original_text and success:
                    print("AVISO: A API não alterou o texto. Tentando novamente com um prompt mais explícito...")
                    translated_block, success = translate_text(original_block, field_name, original_text=original_text, is_retry=True)
                
                translation_history = [translated_block]
                history_index = 0
                is_approved = False
                
                while not is_approved:
                    print_header(f"TRADUÇÃO DE REGISTRO {i+1}/{len(records)}")
                    print(f"Identificador: {record.get('name', record.get('devname', 'N/A'))}")
                    current_block = translation_history[history_index]
                    current_text = extract_field_display_value(current_block, field_name)
                    
                    print(f"\nOriginal ({field_name}):\n{original_text}")
                    print(f"\nTradução proposta ({field_name}) ({history_index + 1}/{len(translation_history)}):\n{current_text}")
                    
                    choice = get_translation_choice(history_index, len(translation_history))
                    
                    if choice == 'approve':
                        translated_blocks[i] = current_block
                        is_approved = True
                        # Atualiza o conteúdo com base no conteúdo original e nas traduções aprovadas
                        updated_content = update_content_fixed(content, positions, translated_blocks)
                        save_file(filename, updated_content)
                        print("Tradução aplicada ao arquivo em tempo real.")
                    
                    elif choice == 'new':
                        print("\nGerando nova tradução...")
                        new_block, success = translate_text(original_block, field_name, current_text, is_retry=True)
                        translation_history.append(new_block)
                        history_index = len(translation_history) - 1
                    
                    elif choice == 'previous':
                        history_index -= 1
                    
                    elif choice == 'next':
                        history_index += 1
                    
                    elif choice == 'original':
                        translated_blocks[i] = original_block
                        is_approved = True
                        updated_content = update_content_fixed(content, positions, translated_blocks)
                        save_file(filename, updated_content)
                        print("Texto original mantido e salvo.")
                    
                    elif choice == 'manual':
                        print("\nEDITANDO MANUALMENTE")
                        print("\nBloco original:")
                        print(original_block)
                        print("\nBloco atual:")
                        print(current_block)
                        print("\nDigite o bloco completo com sua tradução:")
                        manual_block = input("> ")
                        translation_history.append(manual_block)
                        history_index = len(translation_history) - 1
                    
                    elif choice == 'quit':
                        print("\nOperação cancelada pelo usuário.")
                        sys.exit(0)
        
        print_header("CONCLUSÃO")
        print("Processo de tradução concluído com sucesso!")
        input("Pressione Enter para sair...")
    
    except KeyboardInterrupt:
        print("\n\nOperação cancelada pelo usuário. As traduções já aprovadas foram salvas.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nErro inesperado: {e}")
        input("Pressione Enter para sair...")
        sys.exit(1)


if __name__ == "__main__":
    main()
