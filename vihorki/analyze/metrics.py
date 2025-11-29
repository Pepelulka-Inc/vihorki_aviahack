from download_data import downloads
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime


def get_metrics():
    hits = pd.read_hdf("data/hits.h5", key='df')
    visits = pd.read_hdf("data/visits_f.h5", key='df')
    joins = downloads(2022)
    joins_2024 = downloads(2024)
    n = int(input())
    if n == 1:
        report = analyze_and_visualize_wandering(joins, pageview_threshold=8)
        print(report)
    else:
        report = visualize_backtracks_analysis(joins)
        print(report)
    return 

def detect_wandering(joined_df, pageview_threshold=8):
    sessions = joined_df.groupby('visitID').agg({
        'URL':'nunique',
        'watchID':'count',
        'dateTime_visit':'min'
    }).rename(columns={'watchID':'hits','URL':'unique_pages'})
    # wandering — много переходов
    sessions['is_wandering'] = (sessions['hits'] >= pageview_threshold)
    return sessions[sessions['is_wandering']].sort_values('hits', ascending=False)

def analyze_and_visualize_wandering(joined_df, pageview_threshold=8):
    """
    Комплексный анализ и визуализация wandering sessions
    """
    # Вычисляем метрику
    wandering_sessions = detect_wandering(joined_df, pageview_threshold)
    
    if wandering_sessions.empty:
        print("❌ Нет wandering sessions для анализа")
        return
    
    # Создаем фигуру с несколькими subplots
    fig, axes = plt.subplots(2, 1, figsize=(15, 10))
    fig.suptitle(f'Анализ Wandering Sessions (порог: {pageview_threshold}+ хитов)', 
                 fontsize=16, fontweight='bold')
    
    # 1. Распределение уникальных страниц
    axes[0].hist(wandering_sessions['unique_pages'], bins=15, alpha=0.7, color='lightgreen', edgecolor='black')
    axes[0].axvline(wandering_sessions['unique_pages'].mean(), color='red', linestyle='--',
                      label=f'Среднее: {wandering_sessions["unique_pages"].mean():.1f}')
    axes[0].set_xlabel('Уникальные страницы')
    axes[0].set_ylabel('Количество сессий')
    axes[0].set_title('Распределение уникальных страниц')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # 2. Круговая диаграмма распределения по уровням активности
    activity_levels = pd.cut(wandering_sessions['hits'], 
                           bins=[0, pageview_threshold, 15, float('inf')],
                           labels=['0-8', '9-15', '16+'])
    level_counts = activity_levels.value_counts()
    axes[1].pie(level_counts.values, labels=level_counts.index, autopct='%1.1f%%',
                  colors=['lightblue', 'lightgreen', 'orange', 'red'])
    axes[1].set_title('Распределение по уровням активности')
    
    plt.tight_layout()
    plt.show()
    
    return generate_wandering_report(wandering_sessions, joined_df, pageview_threshold)

def generate_wandering_report(wandering_sessions, joined_df, pageview_threshold):
    """
    Генерация текстового отчета по wandering sessions
    """
    total_sessions = joined_df['visitID'].nunique()
    wandering_count = len(wandering_sessions)
    
    report = []
    report.append("📊 ОТЧЕТ ПО WANDERING SESSIONS")
    report.append("=" * 50)
    
    # Основные метрики
    report.append(f"\n📈 ОСНОВНЫЕ МЕТРИКИ:")
    report.append(f"• Всего сессий: {total_sessions:,}")
    report.append(f"• Wandering sessions: {wandering_count:,} ({wandering_count/total_sessions*100:.1f}%)")
    report.append(f"• Порог активности: {pageview_threshold}+ хитов")
    report.append(f"• Среднее хитов в wandering: {wandering_sessions['hits'].mean():.1f}")
    report.append(f"• Среднее уникальных страниц: {wandering_sessions['unique_pages'].mean():.1f}")
    report.append(f"• Максимум хитов: {wandering_sessions['hits'].max()}")
    
    # Анализ распределения
    report.append(f"\n📊 РАСПРЕДЕЛЕНИЕ АКТИВНОСТИ:")
    quantiles = wandering_sessions['hits'].quantile([0.25, 0.5, 0.75, 0.9, 0.95])
    for q, value in quantiles.items():
        report.append(f"• {int(q*100)}% сессий: до {value:.0f} хитов")
    
    # Сегментация по уровням активности
    activity_segments = pd.cut(wandering_sessions['hits'], 
                             bins=[pageview_threshold, 15, 25, 50, float('inf')],
                             labels=['Низкая (8-15)', 'Средняя (16-25)', 'Высокая (26-50)', 'Экстремальная (50+)'])
    segment_counts = activity_segments.value_counts().sort_index()
    
    report.append(f"\n🎯 СЕГМЕНТАЦИЯ ПО АКТИВНОСТИ:")
    for segment, count in segment_counts.items():
        percentage = count / wandering_count * 100
        report.append(f"• {segment}: {count} сессий ({percentage:.1f}%)")
    
    # Анализ эффективности
    report.append(f"\n💡 ВЫВОДЫ И РЕКОМЕНДАЦИИ:")
    
    if wandering_count / total_sessions > 0.1:
        report.append("⚠️  Высокий процент wandering sessions (>10%). Возможно:")
        report.append("   - Сложная навигация по сайту")
        report.append("   - Неясные цели или CTA")
        report.append("   - Пользователи ищут информацию")
    else:
        report.append("✅ Нормальный уровень wandering sessions")
    
    if wandering_sessions['unique_pages'].mean() / wandering_sessions['hits'].mean() < 0.5:
        report.append("📄 Пользователи часто возвращаются на одни и те же страницы")
        report.append("   Рекомендация: улучшить внутренние ссылки и навигацию")
    else:
        report.append("🌐 Пользователи исследуют разнообразный контент")
    
    # Топ проблемных сессий
    if len(wandering_sessions) > 0:
        report.append(f"\n🔥 ТОП-5 САМЫХ АКТИВНЫХ SESSIONS:")
        top_5 = wandering_sessions.nlargest(5, 'hits')
        for i, (session_id, row) in enumerate(top_5.iterrows(), 1):
            report.append(f"{i}. Session {session_id}: {row['hits']} хитов, {row['unique_pages']} уникальных страниц")
    
    return "\n".join(report)

def count_backtracks(joined_df):
    # grouped by session, sorted by hit time
    def backtracks_for_session(df):
        urls = list(df['URL'].fillna(''))
        bt = 0
        for i in range(2, len(urls)):
            if urls[i] == urls[i-2]:
                bt += 1
        return bt
    bts = joined_df.groupby('visitID').apply(lambda df: backtracks_for_session(df.sort_values('dateTime_hit')))
    return bts.rename('backtracks').reset_index()


def visualize_backtracks_analysis(joined_df):
    """
    Визуализация и анализ метрики возвратов (backtracks)
    """
    # Вычисляем метрику
    backtracks_df = count_backtracks(joined_df)
    
    if backtracks_df.empty:
        print("❌ Нет данных для анализа backtracks")
        return
    
    # Создаем фигуру с двумя графиками
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 1. Распределение количества backtracks по сессиям
    ax1.hist(backtracks_df['backtracks'], bins=20, alpha=0.7, color='lightcoral', 
             edgecolor='black', linewidth=0.5)
    ax1.axvline(backtracks_df['backtracks'].mean(), color='red', linestyle='--', 
                linewidth=2, label=f'Среднее: {backtracks_df["backtracks"].mean():.2f}')
    ax1.axvline(backtracks_df['backtracks'].median(), color='blue', linestyle='--', 
                linewidth=2, label=f'Медиана: {backtracks_df["backtracks"].median():.1f}')
    
    ax1.set_xlabel('Количество возвратов (backtracks)')
    ax1.set_ylabel('Количество сессий')
    ax1.set_title('Распределение возвратов по сессиям', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. Доля сессий с возвратами
    sessions_with_backtracks = (backtracks_df['backtracks'] > 0).sum()
    total_sessions = len(backtracks_df)
    sessions_without_backtracks = total_sessions - sessions_with_backtracks
    
    labels = ['С возвратами', 'Без возвратов']
    sizes = [sessions_with_backtracks, sessions_without_backtracks]
    colors = ['lightcoral', 'lightblue']
    
    ax2.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', 
            startangle=90, textprops={'fontsize': 12})
    ax2.set_title('Доля сессий с возвратами', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.show()
    
    # Генерация отчета
    return generate_backtracks_report(backtracks_df)

def generate_backtracks_report(backtracks_df):
    """
    Генерация текстового отчета по метрике backtracks
    """
    total_sessions = len(backtracks_df)
    sessions_with_backtracks = (backtracks_df['backtracks'] > 0).sum()
    max_backtracks = backtracks_df['backtracks'].max()
    
    report = []
    report.append("🔄 АНАЛИЗ МЕТРИКИ ВОЗВРАТОВ (BACKTRACKS)")
    report.append("=" * 45)
    
    # Основные метрики
    report.append(f"\n📊 ОСНОВНЫЕ ПОКАЗАТЕЛИ:")
    report.append(f"• Всего сессий: {total_sessions:,}")
    report.append(f"• Сессии с возвратами: {sessions_with_backtracks:,} ({sessions_with_backtracks/total_sessions*100:.1f}%)")
    report.append(f"• Среднее возвратов на сессию: {backtracks_df['backtracks'].mean():.2f}")
    report.append(f"• Медиана возвратов: {backtracks_df['backtracks'].median():.1f}")
    report.append(f"• Максимум возвратов: {max_backtracks}")
    
    # Анализ распределения
    report.append(f"\n📈 РАСПРЕДЕЛЕНИЕ:")
    quantiles = backtracks_df['backtracks'].quantile([0.5, 0.75, 0.9, 0.95, 0.99])
    report.append(f"• 50% сессий: до {quantiles[0.5]:.0f} возвратов")
    report.append(f"• 75% сессий: до {quantiles[0.75]:.0f} возвратов") 
    report.append(f"• 90% сессий: до {quantiles[0.9]:.0f} возвратов")
    
    if max_backtracks > quantiles[0.9]:
        report.append(f"• Есть выбросы: до {max_backtracks} возвратов")
    
    # Сегментация сессий
    report.append(f"\n🎯 СЕГМЕНТАЦИЯ СЕССИЙ:")
    segments = pd.cut(backtracks_df['backtracks'], 
                     bins=[-1, 0, 2, 5, float('inf')],
                     labels=['0 возвратов', '1-2 возврата', '3-5 возвратов', '6+ возвратов'])
    
    for segment in segments.cat.categories:
        count = (segments == segment).sum()
        percentage = count / total_sessions * 100
        report.append(f"• {segment}: {count} сессий ({percentage:.1f}%)")
    
    # Интерпретация и рекомендации
    report.append(f"\n💡 ИНТЕРПРЕТАЦИЯ:")
    
    mean_backtracks = backtracks_df['backtracks'].mean()
    if mean_backtracks > 2:
        report.append("⚠️  Высокий уровень возвратов. Возможные причины:")
        report.append("   - Сложная навигация по сайту")
        report.append("   - Пользователи теряются в структуре")
        report.append("   - Неясный путь к цели")
        report.append("   📝 Рекомендация: упростить навигацию, добавить хлебные крошки")
    elif mean_backtracks > 0.5:
        report.append("✅ Умеренный уровень возвратов")
        report.append("   - Пользователи исследуют контент")
        report.append("   - Нормальное поведение при поиске информации")
    else:
        report.append("🎉 Отличный показатель!")
        report.append("   - Пользователи легко находят нужную информацию")
        report.append("   - Эффективная навигация")
    
    # Проблемные сессии
    problematic_sessions = backtracks_df[backtracks_df['backtracks'] > 5]
    if len(problematic_sessions) > 0:
        report.append(f"\n🚨 ПРОБЛЕМНЫЕ СЕССИИ (>5 возвратов): {len(problematic_sessions)} шт.")
        report.append("   Требуют детального анализа пользовательского пути")
    
    return "\n".join(report)


if __name__ == "__main__":
    get_metrics()