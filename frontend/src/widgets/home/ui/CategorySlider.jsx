import { useRef } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Container } from "@shared/ui"
import CategoryCard from "./CategoryCard";
import { categories } from "@shared/config"

export default function CategorySlider() {
  const scrollRef = useRef(null);

  const scroll = (direction) => {
    const container = scrollRef.current;
    const scrollAmount = 300;

    if (!container) return;

    container.scrollBy({
      left: direction === "left" ? -scrollAmount : scrollAmount,
      behavior: "smooth",
    });
  };

  return (
    <section className="-mt-12 relative z-30">
      <Container>
        <div className="relative bg-white rounded-2xl shadow-xl">

          {/* LEFT BUTTON */}
          <button
            onClick={() => scroll("left")}
            className="hidden md:flex absolute left-2 top-1/2 -translate-y-1/2 z-10
                       bg-white shadow w-10 h-10 rounded-full items-center justify-center"
          >
            <ChevronLeft size={20} />
          </button>

          {/* SCROLL CONTAINER */}
          <div
            ref={scrollRef}
            className="flex overflow-x-auto scroll-smooth no-scrollbar"
          >
            {categories.map((category) => (
              <CategoryCard
                key={category.id}
                category={category}
              />
            ))}
          </div>

          {/* RIGHT BUTTON */}
          <button
            onClick={() => scroll("right")}
            className="hidden md:flex absolute right-2 top-1/2 -translate-y-1/2 z-10
                       bg-white shadow w-10 h-10 rounded-full items-center justify-center"
          >
            <ChevronRight size={20} />
          </button>

        </div>
      </Container>
    </section>
  );
}
