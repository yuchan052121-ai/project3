import ast
import numpy as np
import pandas as pd
from gensim import corpora, models

class TopicBasedRecommender():
    def __init__(self, df_grad=None, num_topics=6):
        self.user_profile = None
        self.user_profile_percent = None
        self.num_topics = num_topics
        # データの読み込み
        self.df_combined = pd.read_csv("キーワード_拡大版_社会工学類.csv", encoding='utf-8')
        self.df_social_courses = pd.read_csv("社会工学類授業_df(Sheet1).csv", encoding='utf-8')
        self.df_grad = self.df_social_courses 

    def assign_info_to_courses(self):
        def return_syllabus_link(class_str):
            return f'https://kdb.tsukuba.ac.jp/syllabi/2024/{class_str}/jpn'

        self.df_combined.columns = [c.strip() for c in self.df_combined.columns]
        self.df_social_courses.columns = [c.strip() for c in self.df_social_courses.columns]

        def safe_literal_eval(val):
            if pd.isna(val) or val == "": return []
            if isinstance(val, list): return val
            val_str = str(val).strip()
            clean_val = val_str.lstrip('[').rstrip(']')
            keywords = [w.strip().strip("'").strip('"') for w in clean_val.split(',') if w.strip()]
            return keywords

        target_col = '拡張キーワード' if '拡張キーワード' in self.df_combined.columns else 'キーワード'
        self.df_combined['キーワード'] = self.df_combined[target_col].apply(safe_literal_eval)
        
        target_social_col = '拡張キーワード' if '拡張キーワード' in self.df_social_courses.columns else 'キーワード'
        self.df_social_courses['キーワード'] = self.df_social_courses[target_social_col].apply(safe_literal_eval)
        
        self.df_social_courses['シラバス'] = self.df_social_courses['科目番号'].apply(return_syllabus_link)
        if '授業科目名' not in self.df_social_courses.columns:
            self.df_social_courses = self.df_social_courses.rename(columns={'科目名': '授業科目名'})

    def train_lda(self):
        texts = self.df_combined['キーワード']
        self.dictionary = corpora.Dictionary(texts)
        corpus = [self.dictionary.doc2bow(text) for text in texts]
        self.lda_model = models.LdaModel(
            corpus=corpus, id2word=self.dictionary, num_topics=self.num_topics,
            random_state=42, passes=10
        )

    def update_user_profile(self, user_ratings):
        """評価値(1-5)を重みとして加重平均を計算"""
        user_ratings = np.array(user_ratings)
        texts = self.df_combined['キーワード']
        corpus = [self.dictionary.doc2bow(text) for text in texts]
        
        topic_distributions = []
        for doc in corpus:
            dist = self.lda_model.get_document_topics(doc, minimum_probability=0)
            topic_distributions.append([prob for _, prob in dist])

        topic_distributions = np.array(topic_distributions)
        rated_indices = np.where(user_ratings > 0)[0]

        if len(rated_indices) == 0:
            self.user_profile = np.full(self.num_topics, 1.0 / self.num_topics)
        else:
            relevant_dists = topic_distributions[rated_indices]
            relevant_ratings = user_ratings[rated_indices]
            # 評価値を重みとした加重平均
            self.user_profile = np.average(relevant_dists, axis=0, weights=relevant_ratings)

        denom = self.user_profile.sum()
        self.user_profile_percent = (self.user_profile / denom * 100).astype(int) if denom > 0 else np.zeros(self.num_topics)

    def _number_to_char(self, number):
        # Colabの最新定義に更新
        topic_number_dict = {
            0: "数理基礎", 
            1: "経済分析・金融統計", 
            2: "建築設計・都市開発",
            3: "公共政策・行政経済", 
            4: "数理モデル・統計解析", 
            5: "都市構造・地理空間"
        }
        return topic_number_dict.get(number, f"トピック{number}")

    def assign_topic_to_courses(self):
        def get_relevance(doc):
            bow = self.dictionary.doc2bow(doc)
            dist = self.lda_model.get_document_topics(bow, minimum_probability=0)
            probs = [prob for _, prob in dist]
            return np.argmax(probs), np.max(probs)

        results = self.df_social_courses['キーワード'].apply(get_relevance)
        self.df_social_courses['関連トピック'] = results.apply(lambda x: x[0])
        self.df_social_courses['トピック比率'] = results.apply(lambda x: x[1])
        self.df_social_courses['トピック'] = self.df_social_courses['関連トピック'].apply(self._number_to_char)
        self.df_social_courses['トピック選好'] = self.df_social_courses['関連トピック'].apply(lambda x: self.user_profile[x])
        self.df_social_courses['推薦スコア'] = self.df_social_courses['トピック選好'] * self.df_social_courses['トピック比率']

    def get_social_recommendations_as_dict(self, top_n=50):
        self.assign_topic_to_courses()
        res = self.df_social_courses.sort_values(by='推薦スコア', ascending=False).head(top_n)
        return res.to_dict('records')