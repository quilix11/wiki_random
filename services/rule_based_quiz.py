import re
import random
import logging
from typing import List, Dict, Optional, Tuple, Set

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- Pseudo-spaCy classes for standard library support ---
class PseudoToken:
    def __init__(self, text: str):
        self.text = text
        self.pos_ = self._guess_pos()
        self.is_punct = bool(re.match(r'[^\w\s]', text))
        self.is_space = text.isspace()
        self.like_num = bool(re.search(r'\d+', text))

    def _guess_pos(self) -> str:
        if re.search(r'\d+', self.text): return 'NUM'
        if self.text[0].isupper() and len(self.text) > 1: return 'PROPN'
        if len(self.text) > 3: return 'NOUN'
        return 'OTHER'

    def __len__(self):
        return len(self.text)

class PseudoSpan:
    def __init__(self, text: str):
        self.text = text
        # Simple entity recognition
        self.ents = []
        # Dates (Years)
        for m in re.finditer(r'\b\d{4}\b', text):
            self.ents.append(type('Ent', (), {'text': m.group(), 'label_': 'DATE'})())
        # Capitalized words (Potential PER, LOC, ORG)
        for m in re.finditer(r'\b[А-ЩЬЮЯҐЄІЇ][а-щьюяґєії\']+\b', text):
            self.ents.append(type('Ent', (), {'text': m.group(), 'label_': 'PROPN'})())
        
        # Tokenization
        self.tokens = [PseudoToken(t) for t in re.findall(r'\w+|[^\w\s]', text)]

    def __iter__(self):
        return iter(self.tokens)

    def __len__(self):
        return len(self.tokens)

class PseudoDoc:
    def __init__(self, text: str):
        self.text = text
        self.sents = [PseudoSpan(s.strip()) for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        self.ents = []
        for s in self.sents:
            self.ents.extend(s.ents)
        self.tokens = []
        for s in self.sents:
            self.tokens.extend(s.tokens)

    def __iter__(self):
        return iter(self.tokens)

def nlp(text: str) -> PseudoDoc:
    return PseudoDoc(text)

# --- Original classes adapted to use PseudoDoc/PseudoSpan ---

class TextPreprocessor:
    """Клас для очищення та підготовки тексту перед аналізом."""
    @staticmethod
    def clean_text(text: str) -> str:
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\[джерело\?\]', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.replace(' - ', ' — ')
        return text.strip()

class SentenceScorer:
    """Клас для оцінки того, наскільки речення підходить для питання."""
    MIN_WORDS = 6
    MAX_WORDS = 40
    
    @classmethod
    def score_sentence(cls, sentence: PseudoSpan) -> float:
        text = sentence.text
        words = [token for token in sentence if not token.is_punct and not token.is_space]
        if len(words) < cls.MIN_WORDS or len(words) > cls.MAX_WORDS:
            return 0.0
            
        score = 0.5
        first_word = words[0].text.lower()
        if first_word in ['він', 'вона', 'воно', 'вони', 'цей', 'ця', 'це', 'такий']:
            score -= 0.3
        if len(sentence.ents) > 0:
            score += 0.3
        if ' — ' in text or ' є ' in text or ' називають ' in text:
            score += 0.4
        return min(max(score, 0.0), 1.0)

class DistractorGenerator:
    """Клас для розумної генерації неправильних варіантів відповідей."""
    def __init__(self, doc: PseudoDoc):
        self.doc = doc
        self._build_entity_pools()
        
    def _build_entity_pools(self):
        self.pools: Dict[str, Set[str]] = {
            'PROPN': set(),
            'NOUNS': set()
        }
        for ent in self.doc.ents:
            if ent.label_ == 'PROPN':
                self.pools['PROPN'].add(ent.text)
        for token in self.doc:
            if token.pos_ == 'NOUN' and len(token.text) > 3:
                self.pools['NOUNS'].add(token.text.lower())
                
    def get_number_distractors(self, target: str, count: int = 3) -> List[str]:
        try:
            val_str = re.sub(r'[^\d.]', '', target.replace(',', '.'))
            val = float(val_str)
            is_int = val.is_integer()
            val = int(val) if is_int else val
            
            distractors = set()
            if is_int and 1000 < val < 2100:
                offsets = [-50, -20, -10, -5, -2, 2, 5, 10, 20, 50]
                while len(distractors) < count:
                    distractors.add(str(val + random.choice(offsets)))
            else:
                offsets = [0.5, 0.8, 0.9, 1.1, 1.2, 1.5, 2.0]
                while len(distractors) < count:
                    new_val = val * random.choice(offsets)
                    if is_int:
                        distractors.add(str(int(new_val) + random.randint(-2, 2)))
                    else:
                        distractors.add(f"{new_val:.1f}")
            return list(distractors)[:count]
        except (ValueError, ZeroDivisionError):
            return ["Близько 10", "Понад 100", "Менше 5"][:count]

    def get_entity_distractors(self, target: str, label: str, count: int = 3) -> List[str]:
        pool = list(self.pools.get(label, set()) - {target})
        if len(pool) >= count:
            return random.sample(pool, count)
        fallbacks = ['Київ', 'Лондон', 'Україна', 'Європа', 'США', 'Тарас Шевченко', 'ООН']
        pool.extend([f for f in fallbacks if f != target])
        return list(set(pool))[:count]

class QuestionGenerator:
    """Головний клас для створення питань."""
    def __init__(self, doc: PseudoDoc, distractor_gen: DistractorGenerator):
        self.doc = doc
        self.distractor_gen = distractor_gen

    def _create_question_dict(self, sentence: str, target: str, distractors: List[str]) -> dict:
        question_text = sentence.replace(target, "_______", 1)
        options = distractors + [target]
        random.shuffle(options)
        
        return {
            "text": f"Заповніть пропуск у реченні:\n\"{question_text}\"",
            "options": options,
            "correct": options.index(target)
        }

    def generate_from_entities(self, sentence: PseudoSpan) -> Optional[dict]:
        valid_ents = [ent for ent in sentence.ents if ent.label_ == 'PROPN']
        if not valid_ents: return None
        target_ent = random.choice(valid_ents)
        distractors = self.distractor_gen.get_entity_distractors(target_ent.text, target_ent.label_)
        return self._create_question_dict(sentence.text, target_ent.text, distractors)

    def generate_from_numbers(self, sentence: PseudoSpan) -> Optional[dict]:
        numbers = [token for token in sentence if token.pos_ == 'NUM' or token.like_num]
        if not numbers: return None
        target_token = random.choice(numbers)
        if not re.search(r'\d+', target_token.text): return None
        distractors = self.distractor_gen.get_number_distractors(target_token.text)
        return self._create_question_dict(sentence.text, target_token.text, distractors)
        
    def generate_from_nouns(self, sentence: PseudoSpan) -> Optional[dict]:
        nouns = [token for token in sentence if token.pos_ == 'NOUN' and len(token.text) > 4]
        if not nouns: return None
        target_token = sorted(nouns, key=lambda x: len(x.text), reverse=True)[0]
        pool = list(self.distractor_gen.pools['NOUNS'] - {target_token.text.lower()})
        distractors = random.sample(pool, min(len(pool), 3))
        while len(distractors) < 3:
            distractors.append(f"Альтернатива {len(distractors)+1}")
        return self._create_question_dict(sentence.text, target_token.text, distractors)

class QuizPipeline:
    """Оркестратор процесу генерації."""
    def __init__(self):
        pass

    def generate(self, text: str, num_questions: int = 3) -> Dict[str, List[dict]]:
        clean_text = TextPreprocessor.clean_text(text)
        doc = nlp(clean_text)
        
        sentences_with_scores = []
        for sent in doc.sents:
            score = SentenceScorer.score_sentence(sent)
            if score > 0.3:
                sentences_with_scores.append((score, sent))
                
        sentences_with_scores.sort(key=lambda x: x[0], reverse=True)
        distractor_gen = DistractorGenerator(doc)
        question_gen = QuestionGenerator(doc, distractor_gen)
        
        generated_questions = []
        used_targets = set()
        
        for score, sent in sentences_with_scores:
            if len(generated_questions) >= num_questions:
                break
            
            q_dict = question_gen.generate_from_entities(sent)
            if not q_dict:
                q_dict = question_gen.generate_from_numbers(sent)
            if not q_dict and score > 0.6:
                q_dict = question_gen.generate_from_nouns(sent)
                
            if q_dict:
                correct_answer = q_dict["options"][q_dict["correct"]]
                if correct_answer.lower() not in used_targets:
                    generated_questions.append(q_dict)
                    used_targets.add(correct_answer.lower())
                    
        return {"questions": generated_questions}

# Функція для сумісності з існуючим кодом
def generate_rule_based_quiz(text: str, title: str) -> Dict[str, List[dict]]:
    pipeline = QuizPipeline()
    return pipeline.generate(text, num_questions=3)
