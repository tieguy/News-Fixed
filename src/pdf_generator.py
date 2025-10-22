"""PDF generation for News, Fixed newspaper."""

from pathlib import Path
from typing import Dict, List
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from src.utils import generate_qr_code, format_date, get_theme_name, extract_source_name


class NewspaperGenerator:
    """Generates print-ready PDF newspapers."""

    def __init__(self, templates_dir: Path = None):
        """
        Initialize the newspaper generator.

        Args:
            templates_dir: Path to templates directory
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent / "templates"

        self.templates_dir = templates_dir
        self.env = Environment(loader=FileSystemLoader(str(templates_dir)))

    def generate_pdf(
        self,
        day_number: int,
        main_story: Dict,
        mini_articles: List[Dict],
        statistics: List[Dict],
        output_path: str,
        date_str: str = None,
        day_of_week: str = None,
        front_page_stories: List[Dict] = None,
        feature_box: Dict = None,
        tomorrow_teaser: str = ""
    ) -> Path:
        """
        Generate a 2-page newspaper PDF.

        Args:
            day_number: Day number (1-4)
            main_story: Main story dict with 'title', 'content', and 'source_url'
            mini_articles: List of mini article dicts with 'title', 'content', 'source_url'
            statistics: List of stat dicts with 'number' and 'description'
            output_path: Output PDF file path
            date_str: Date string (formatted or ISO format) or None for today
            day_of_week: Day of week name (e.g., "Monday") or None
            front_page_stories: List of 2-3 secondary stories for front page
            feature_box: Optional feature box dict with 'title' and 'content'
            tomorrow_teaser: Tomorrow teaser text

        Returns:
            Path to generated PDF
        """
        # Get theme for this day
        theme = get_theme_name(day_number)

        # Format date (if it's already formatted, use as-is; otherwise format it)
        if date_str and (',' in date_str or len(date_str) > 10):
            # Already formatted like "October 21, 2025"
            date_formatted = date_str
        else:
            # ISO format or None, needs formatting
            date_formatted = format_date(date_str)

        # Use provided day_of_week or default to "DAY X OF 4"
        if day_of_week is None:
            day_of_week = f"DAY {day_number} OF 4"

        # Generate QR codes for main story
        main_story_with_qr = {
            **main_story,
            "qr_code": generate_qr_code(main_story["source_url"]),
            "source_name": extract_source_name(main_story["source_url"])
        }

        # Generate QR codes for front page stories
        if front_page_stories is None:
            front_page_stories = []

        front_page_stories_with_qr = [
            {
                **article,
                "qr_code": generate_qr_code(article["source_url"]),
                "source_name": extract_source_name(article["source_url"])
            }
            for article in front_page_stories
        ]

        # Generate QR codes for mini articles
        mini_articles_with_qr = [
            {
                **article,
                "qr_code": generate_qr_code(article["source_url"]),
                "source_name": extract_source_name(article["source_url"])
            }
            for article in mini_articles
        ]

        # Prepare template context
        context = {
            "day_number": day_number,
            "day_of_week": day_of_week,
            "date": date_formatted,
            "theme": theme,
            "main_story": main_story_with_qr,
            "front_page_stories": front_page_stories_with_qr,
            "mini_articles": mini_articles_with_qr,
            "statistics": statistics,
            "feature_box": feature_box,
            "tomorrow_teaser": tomorrow_teaser,
            "footer_message": "Good news exists, but it travels slowly."
        }

        # Load template
        template = self.env.get_template("newspaper.html")
        html_content = template.render(**context)

        # Load CSS
        css_path = self.templates_dir / "styles.css"

        # Generate PDF
        html = HTML(string=html_content, base_url=str(self.templates_dir))
        css = CSS(filename=str(css_path))

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        html.write_pdf(output_file, stylesheets=[css])

        return output_file


if __name__ == "__main__":
    # Test PDF generation with sample data
    print("Testing NewspaperGenerator...")

    generator = NewspaperGenerator()

    # Sample data
    main_story = {
        "title": "Scientists Discover Bacteria That Eat Ocean Plastic",
        "content": """A team of researchers has made an exciting breakthrough in the fight against ocean pollution. They've discovered bacteria that can break down plastic waste in the ocean, potentially offering a natural solution to one of our planet's biggest environmental challenges.

The bacteria, found in coastal waters, can digest certain types of plastic in just a few weeks—much faster than the hundreds of years it normally takes for plastic to decompose. The scientists estimate that with further development, this discovery could help clean up millions of tons of plastic from our oceans.

What makes this even more remarkable is that these bacteria occur naturally. Scientists didn't have to create them in a lab; they just had to find them and understand how they work. It's like discovering that nature already had a solution to a problem we thought only technology could solve.

The research team is now working on ways to boost the bacteria's plastic-eating abilities and deploy them safely in polluted areas. They're also studying whether similar bacteria might exist in other parts of the ocean.

This discovery shows how much we still have to learn from nature. While we still need to reduce our plastic use and improve recycling, it's encouraging to know that natural solutions might help us clean up past mistakes. As one researcher put it: "We created the plastic problem, but nature might help us solve it."

For young people who care about the environment, this is a reminder that scientific discovery can unlock unexpected solutions. The ocean's tiny bacteria might just be heroes in disguise.""",
        "source_url": "https://www.nature.com/articles/example-plastic-bacteria"
    }

    mini_articles = [
        {
            "title": "Solar Power Reaches Record Low Prices",
            "content": "Solar energy costs have dropped by 90% in the last decade, making it cheaper than fossil fuels in most countries. Over 100 countries now get at least 10% of their electricity from solar and wind power. This means cleaner air and more affordable energy for millions of families worldwide.",
            "source_url": "https://www.iea.org/solar-report"
        },
        {
            "title": "Teen Inventors Create Water Filter",
            "content": "Three high school students in Kenya invented a low-cost water filter using local materials. Their device can clean 20 liters of water per hour and costs less than $5 to build. The filter removes 99% of harmful bacteria, providing clean drinking water to communities that need it most.",
            "source_url": "https://www.unicef.org/innovation/water-filter"
        },
        {
            "title": "Forests Growing Faster Than Expected",
            "content": "New satellite data shows that reforestation efforts are working better than predicted. Areas that were deforested 20 years ago are now home to thriving forests with diverse wildlife. Scientists say this proves that when we give nature a chance, it can recover remarkably fast.",
            "source_url": "https://www.conservation.org/forest-recovery"
        },
        {
            "title": "Girls' Education Reaches All-Time High",
            "content": "For the first time in history, more than 90% of girls worldwide are enrolled in primary school. Countries that invested in girls' education are seeing benefits across health, economy, and innovation. One expert called it 'the most powerful investment any society can make.'",
            "source_url": "https://www.unesco.org/education-report"
        }
    ]

    statistics = [
        {"number": "90%", "description": "drop in solar costs"},
        {"number": "100+", "description": "countries using clean energy"},
        {"number": "$5", "description": "cost of water filter"},
        {"number": "99%", "description": "bacteria removed"},
        {"number": "20 years", "description": "for forests to recover"},
        {"number": "90%", "description": "girls in school globally"}
    ]

    feature_box = {
        "title": "Quick Win",
        "content": "Over 50 countries have banned single-use plastic bags, reducing ocean plastic by millions of tons annually."
    }

    tomorrow_teaser = "Tomorrow: How young activists are leading the charge on climate action, plus a breakthrough in clean energy storage."

    # Generate PDF
    output_path = Path(__file__).parent.parent / "output" / "test_newspaper.pdf"

    print(f"\nGenerating test newspaper: {output_path}")

    generated_file = generator.generate_pdf(
        day_number=1,
        main_story=main_story,
        mini_articles=mini_articles,
        statistics=statistics,
        output_path=str(output_path),
        feature_box=feature_box,
        tomorrow_teaser=tomorrow_teaser
    )

    print(f"\n✓ PDF generated successfully: {generated_file}")
    print(f"  File size: {generated_file.stat().st_size / 1024:.1f} KB")
    print(f"\nOpen it with: xdg-open {generated_file}")
