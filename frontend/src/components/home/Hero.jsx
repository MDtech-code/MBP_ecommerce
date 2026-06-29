import {
  ArrowRight,
} from "lucide-react";


import Container from "../common/Container";
import HeroBenefits from "./HeroBenefits";


import bikeHero from "../../assets/images/hero/bike-hero-1.png";


export default function Hero() {


  return (

    <section
      className="
        relative
        overflow-hidden
        bg-dark
        min-h-130
      "
    >


      {/* Background red glow */}

      <div
        className="
          absolute
          right-0
          top-0
          w-150
          h-full
          bg-primary/10
          blur-3xl
        "
      />



      <Container>


        <div
          className="
            relative
            min-h-130
            flex
            items-center
          "
        >



          {/* Left Content */}

          <div
            className="
              relative
              z-20
              w-full
              lg:w-1/2
            "
          >


            <h1
              className="
                text-white
                text-3xl
                lg:text-5xl
                font-black
                italic
                leading-none
              "
            >

              PREMIUM BIKE PARTS

              <br />

              <span className="text-primary">

                FOR EVERY RIDE

              </span>


            </h1>



            <p
              className="
                text-white
                mt-5
                text-lg
                font-semibold
              "
            >

              Original Parts

              <span className="text-primary mx-2">
                •
              </span>


              Best Prices


              <span className="text-primary mx-2">
                •
              </span>


              Fast Delivery Across Pakistan


            </p>




            <button
              className="
                mt-7
                bg-primary
                text-white
                px-7
                py-3
                rounded-md
                font-bold
                flex
                items-center
                gap-3
              "
            >

              SHOP NOW


              <ArrowRight size={20}/>


            </button>




            <HeroBenefits  direction="horizontal" showDivider={true} />


          </div>





          {/* Bike Image */}

          <div
            className="
              absolute
              -right-10
              bottom-0
              lg:w-187.5
              z-10
            "
          >

            <img
              src={bikeHero}
              alt="Sport Bike"
              className="
                w-full
                object-contain
              "
            />


          </div>




        </div>


      </Container>


    </section>

  );

}