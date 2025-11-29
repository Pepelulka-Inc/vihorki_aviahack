from download_data import downloads
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def compare_versions_analysis():
    """
    Сравнительный анализ метрик между версиями сайта 2022 и 2024 года
    """
    # Загружаем данные для обеих версий
    joins_2022 = downloads(2022)
    joins_2024 = downloads(2024)
    
    print("🔄 ЗАГРУЗКА ДАННЫХ...")
    print(f"Данные 2022: {len(joins_2022):,} строк")
    print(f"Данные 2024: {len(joins_2024):,} строк")
    
    # Сравниваем обе метрики для обеих версий
    compare_wandering_metrics(joins_2022, joins_2024)
    compare_backtracks_metrics(joins_2022, joins_2024)
    
    # Сводный отчет
    generate_comparison_summary(joins_2022, joins_2024)

def compare_wandering_metrics(joins_2022, joins_2024, pageview_threshold=8):
    """
    Сравнение метрики Wandering Sessions между версиями
    """
    print("\n" + "="*60)
    print("📊 СРАВНЕНИЕ WANDERING SESSIONS (2022 vs 2024)")
    print("="*60)
    
    # Вычисляем метрики для обеих версий
    wandering_2022 = detect_wandering(joins_2022, pageview_threshold)
    wandering_2024 = detect_wandering(joins_2024, pageview_threshold)
    
    # Основные показатели
    total_2022 = len(set(joins_2022['visitID']))
    total_2024 = len(set(joins_2024['visitID']))
    
    wandering_count_2022 = len(wandering_2022)
    wandering_count_2024 = len(wandering_2024)
    
    wandering_rate_2022 = wandering_count_2022 / total_2022 * 100
    wandering_rate_2024 = wandering_count_2024 / total_2024 * 100
    
    # Визуализация сравнения
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Сравнение Wandering Sessions: 2022 vs 2024', fontsize=16, fontweight='bold')
    
    # 1. Доля wandering sessions
    years = ['2022', '2024']
    wandering_rates = [wandering_rate_2022, wandering_rate_2024]
    bars = ax1.bar(years, wandering_rates, color=['skyblue', 'lightgreen'], alpha=0.7)
    ax1.set_ylabel('Доля wandering sessions (%)')
    ax1.set_title('Доля сессий с высоким количеством хитов')
    ax1.grid(True, alpha=0.3)
    
    # Добавляем значения на столбцы
    for bar, rate in zip(bars, wandering_rates):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    # 2. Среднее количество хитов
    avg_hits_2022 = wandering_2022['hits'].mean() if not wandering_2022.empty else 0
    avg_hits_2024 = wandering_2024['hits'].mean() if not wandering_2024.empty else 0
    
    avg_hits = [avg_hits_2022, avg_hits_2024]
    bars = ax2.bar(years, avg_hits, color=['lightcoral', 'orange'], alpha=0.7)
    ax2.set_ylabel('Среднее количество хитов')
    ax2.set_title('Средняя активность в wandering sessions')
    ax2.grid(True, alpha=0.3)
    
    for bar, hits in zip(bars, avg_hits):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{hits:.1f}', ha='center', va='bottom', fontweight='bold')
    
    # 3. Среднее уникальных страниц
    avg_pages_2022 = wandering_2022['unique_pages'].mean() if not wandering_2022.empty else 0
    avg_pages_2024 = wandering_2024['unique_pages'].mean() if not wandering_2024.empty else 0
    
    avg_pages = [avg_pages_2022, avg_pages_2024]
    bars = ax3.bar(years, avg_pages, color=['plum', 'pink'], alpha=0.7)
    ax3.set_ylabel('Среднее уникальных страниц')
    ax3.set_title('Разнообразие контента в wandering sessions')
    ax3.grid(True, alpha=0.3)
    
    for bar, pages in zip(bars, avg_pages):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{pages:.1f}', ha='center', va='bottom', fontweight='bold')
    
    # 4. Изменение в процентах
    changes = {
        'Доля wandering': ((wandering_rate_2024 - wandering_rate_2022) / wandering_rate_2022 * 100) if wandering_rate_2022 > 0 else 0,
        'Средние хиты': ((avg_hits_2024 - avg_hits_2022) / avg_hits_2022 * 100) if avg_hits_2022 > 0 else 0,
        'Уникальные страницы': ((avg_pages_2024 - avg_pages_2022) / avg_pages_2022 * 100) if avg_pages_2022 > 0 else 0
    }
    
    metrics = list(changes.keys())
    change_values = list(changes.values())
    colors = ['green' if x <= 0 else 'red' for x in change_values]
    
    bars = ax4.bar(metrics, change_values, color=colors, alpha=0.7)
    ax4.set_ylabel('Изменение (%)')
    ax4.set_title('Изменение показателей (2024 vs 2022)')
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=0, color='black', linestyle='-', alpha=0.8)
    
    for bar, change in zip(bars, change_values):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + (1 if change >= 0 else -1), 
                f'{change:+.1f}%', ha='center', va='bottom' if change >= 0 else 'top', 
                fontweight='bold', color='green' if change <= 0 else 'red')
    
    plt.tight_layout()
    plt.show()
    
    # Текстовый отчет
    print(f"\n📈 WANDERING SESSIONS - ОСНОВНЫЕ ПОКАЗАТЕЛИ:")
    print(f"{'Метрика':<25} {'2022':<10} {'2024':<10} {'Изменение':<15}")
    print("-" * 65)
    print(f"{'Всего сессий':<25} {total_2022:<10,} {total_2024:<10,} {total_2024-total_2022:>+10,}")
    print(f"{'Wandering сессий':<25} {wandering_count_2022:<10,} {wandering_count_2024:<10,} {wandering_count_2024-wandering_count_2022:>+10,}")
    print(f"{'Доля wandering (%)':<25} {wandering_rate_2022:<10.1f} {wandering_rate_2024:<10.1f} {wandering_rate_2024-wandering_rate_2022:>+10.1f}%")
    print(f"{'Средние хиты':<25} {avg_hits_2022:<10.1f} {avg_hits_2024:<10.1f} {avg_hits_2024-avg_hits_2022:>+10.1f}")
    print(f"{'Уникальные страницы':<25} {avg_pages_2022:<10.1f} {avg_pages_2024:<10.1f} {avg_pages_2024-avg_pages_2022:>+10.1f}")

def compare_backtracks_metrics(joins_2022, joins_2024):
    """
    Сравнение метрики Backtracks между версиями
    """
    print("\n" + "="*60)
    print("🔄 СРАВНЕНИЕ BACKTRACKS (2022 vs 2024)")
    print("="*60)
    
    # Вычисляем метрики для обеих версий
    backtracks_2022 = count_backtracks(joins_2022)
    backtracks_2024 = count_backtracks(joins_2024)
    
    # Основные показатели
    total_2022 = len(backtracks_2022)
    total_2024 = len(backtracks_2024)
    
    with_backtracks_2022 = (backtracks_2022['backtracks'] > 0).sum()
    with_backtracks_2024 = (backtracks_2024['backtracks'] > 0).sum()
    
    backtracks_rate_2022 = with_backtracks_2022 / total_2022 * 100
    backtracks_rate_2024 = with_backtracks_2024 / total_2024 * 100
    
    avg_backtracks_2022 = backtracks_2022['backtracks'].mean()
    avg_backtracks_2024 = backtracks_2024['backtracks'].mean()
    
    # Визуализация сравнения
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle('Сравнение Backtracks: 2022 vs 2024', fontsize=16, fontweight='bold')
    
    # 1. Доля сессий с возвратами
    years = ['2022', '2024']
    backtracks_rates = [backtracks_rate_2022, backtracks_rate_2024]
    bars = ax1.bar(years, backtracks_rates, color=['lightblue', 'lightgreen'], alpha=0.7)
    ax1.set_ylabel('Доля сессий с возвратами (%)')
    ax1.set_title('Сессии с проблемами навигации')
    ax1.grid(True, alpha=0.3)
    
    for bar, rate in zip(bars, backtracks_rates):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    # 2. Среднее количество возвратов
    avg_backtracks = [avg_backtracks_2022, avg_backtracks_2024]
    bars = ax2.bar(years, avg_backtracks, color=['lightcoral', 'orange'], alpha=0.7)
    ax2.set_ylabel('Среднее возвратов на сессию')
    ax2.set_title('Интенсивность проблем навигации')
    ax2.grid(True, alpha=0.3)
    
    for bar, avg in zip(bars, avg_backtracks):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                f'{avg:.2f}', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.show()
    
    # Текстовый отчет
    print(f"\n📊 BACKTRACKS - ОСНОВНЫЕ ПОКАЗАТЕЛИ:")
    print(f"{'Метрика':<25} {'2022':<10} {'2024':<10} {'Изменение':<15}")
    print("-" * 65)
    print(f"{'Всего сессий':<25} {total_2022:<10,} {total_2024:<10,} {total_2024-total_2022:>+10,}")
    print(f"{'Сессии с возвратами':<25} {with_backtracks_2022:<10,} {with_backtracks_2024:<10,} {with_backtracks_2024-with_backtracks_2022:>+10,}")
    print(f"{'Доля с возвратами (%)':<25} {backtracks_rate_2022:<10.1f} {backtracks_rate_2024:<10.1f} {backtracks_rate_2024-backtracks_rate_2022:>+10.1f}%")
    print(f"{'Среднее возвратов':<25} {avg_backtracks_2022:<10.2f} {avg_backtracks_2024:<10.2f} {avg_backtracks_2024-avg_backtracks_2022:>+10.2f}")

def generate_comparison_summary(joins_2022, joins_2024):
    """
    Генерация сводного отчета с выводами
    """
    print("\n" + "="*70)
    print("🎯 СВОДНЫЙ ОТЧЕТ С ВЫВОДАМИ")
    print("="*70)
    
    # Вычисляем ключевые метрики
    wandering_2022 = detect_wandering(joins_2022)
    wandering_2024 = detect_wandering(joins_2024)
    
    backtracks_2022 = count_backtracks(joins_2022)
    backtracks_2024 = count_backtracks(joins_2024)
    
    # Ключевые показатели
    total_sessions_2022 = joins_2022['visitID'].nunique()
    total_sessions_2024 = joins_2024['visitID'].nunique()
    
    wandering_rate_2022 = len(wandering_2022) / total_sessions_2022 * 100
    wandering_rate_2024 = len(wandering_2024) / total_sessions_2024 * 100
    
    backtracks_rate_2022 = (backtracks_2022['backtracks'] > 0).sum() / len(backtracks_2022) * 100
    backtracks_rate_2024 = (backtracks_2024['backtracks'] > 0).sum() / len(backtracks_2024) * 100
    
    avg_backtracks_2022 = backtracks_2022['backtracks'].mean()
    avg_backtracks_2024 = backtracks_2024['backtracks'].mean()
    
    # Анализ улучшений/ухудшений
    wandering_change = wandering_rate_2024 - wandering_rate_2022
    backtracks_change = backtracks_rate_2024 - backtracks_rate_2022
    avg_backtracks_change = avg_backtracks_2024 - avg_backtracks_2022
    
    print(f"\n📈 ИЗМЕНЕНИЯ ПОКАЗАТЕЛЕЙ (2024 vs 2022):")
    print(f"• Доля wandering sessions: {wandering_change:+.1f}%")
    print(f"• Доля сессий с возвратами: {backtracks_change:+.1f}%") 
    print(f"• Среднее количество возвратов: {avg_backtracks_change:+.2f}")
    
    print(f"\n💡 КЛЮЧЕВЫЕ ВЫВОДЫ:")
    
    # Анализ wandering sessions
    if wandering_change < -2:
        print("✅ УЛУЧШЕНИЕ: Снизилась доля 'блуждающих' сессий")
        print("   - Пользователи стали более целенаправленными")
        print("   - Улучшилась навигация или структура контента")
    elif wandering_change > 2:
        print("⚠️  УХУДШЕНИЕ: Увеличилась доля 'блуждающих' сессий")
        print("   - Пользователи чаще теряются на сайте")
        print("   - Возможно, усложнилась навигация")
    else:
        print("➡️  СТАБИЛЬНО: Доля 'блуждающих' сессий не изменилась значительно")
    
    # Анализ backtracks
    if backtracks_change < -5:
        print("✅ УЛУЧШЕНИЕ: Значительно снизились проблемы с навигацией")
        print("   - Пользователи реже возвращаются к предыдущим страницам")
        print("   - Улучшилась логика перемещения по сайту")
    elif backtracks_change > 5:
        print("⚠️  УХУДШЕНИЕ: Увеличились проблемы с навигацией")
        print("   - Пользователи чаще теряются и возвращаются назад")
        print("   - Необходимо пересмотреть структуру навигации")
    else:
        print("➡️  СТАБИЛЬНО: Проблемы с навигацией остались на прежнем уровне")
    
    # Общая оценка
    positive_changes = sum([
        wandering_change < -1,
        backtracks_change < -2,
        avg_backtracks_change < -0.1
    ])
    
    negative_changes = sum([
        wandering_change > 1,
        backtracks_change > 2, 
        avg_backtracks_change > 0.1
    ])
    
    print(f"\n🎯 ОБЩАЯ ОЦЕНКА ИЗМЕНЕНИЙ:")
    if positive_changes > negative_changes:
        print("📈 Положительная динамика: UX сайта улучшился")
        print("   - Пользователям стало удобнее работать с сайтом")
    elif negative_changes > positive_changes:
        print("📉 Отрицательная динамика: UX сайта ухудшился")
        print("   - Рекомендуется анализ и улучшение навигации")
    else:
        print("⚖️  Смешанные результаты: некоторые аспекты улучшились, другие ухудшились")
        print("   - Необходим точечный анализ проблемных зон")

def get_metrics():
    """
    Обновленная главная функция с сравнением версий
    """
    print("Выберите тип анализа:")
    print("1 - Сравнение версий 2022 vs 2024")
    print("2 - Анализ wandering sessions для одной версии") 
    print("3 - Анализ backtracks для одной версии")
    
    choice = input("Введите номер (1-3): ").strip()
    
    if choice == "1":
        compare_versions_analysis()
    elif choice == "2":
        year = input("Введите год (2022 или 2024): ").strip()
        joins = downloads(int(year))
        report = analyze_and_visualize_wandering(joins, pageview_threshold=8)
        print(report)
    elif choice == "3":
        year = input("Введите год (2022 или 2024): ").strip()
        joins = downloads(int(year))
        report = visualize_backtracks_analysis(joins)
        print(report)
    else:
        print("Неверный выбор")

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