import {
  ChevronLeft,
  ChevronRight
} from "lucide-react";


import Container from "../common/Container";
import CategoryCard from "./CategoryCard";

import { categories } from "../../data/categories";


export default function CategorySlider() {


  return (

    <section
      className="
        relative
        -mt-16
        z-30
      "
    >


      <Container>


        <div
          className="
            bg-white
            rounded-2xl
            shadow-xl
            overflow-hidden
            flex
            items-center
          "
        >



          <button
            className="
              hidden
              md:flex
              absolute
              -left-1
              bg-white
              shadow
              w-10
              h-10
              rounded-full
              items-center
              justify-center
            "
          >

            <ChevronLeft size={20}/>

          </button>




          <div
            className="
              flex
              w-full
              overflow-hidden
            "
          >

            {
              categories.map((category)=> (

                <CategoryCard
                  key={category.id}
                  category={category}
                />

              ))
            }

          </div>





          <button
            className="
              hidden
              md:flex
              absolute
              -right-1
              bg-white
              shadow
              w-10
              h-10
              rounded-full
              items-center
              justify-center
            "
          >

            <ChevronRight size={20}/>

          </button>



        </div>


      </Container>


    </section>

  );

}