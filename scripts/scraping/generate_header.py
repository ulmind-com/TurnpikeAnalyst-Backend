import os

content = """import { Link, useRouterState } from "@tanstack/react-router";
import { ArrowRight, Menu, Moon, Sun, X } from "lucide-react";
import { AnimatePresence, motion, useMotionValueEvent, useScroll } from "motion/react";
import { useState } from "react";
import { TurnpikeLogo } from "@/components/site/turnpike-logo";
import { usePrefs } from "@/hooks/use-prefs";
import { useSession, useUpdateProfile } from "@/hooks/use-auth";
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuList,
  NavigationMenuTrigger,
} from "@/components/ui/navigation-menu";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { SERVICES, INDUSTRIES, DIGITAL_CONTENT, TRAINING, CONTACT_US } from "./mega-menu-content";

export function SiteHeader({ revealOnScroll = false }: { revealOnScroll?: boolean }) {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { scrollY } = useScroll();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const { dark, setPref } = usePrefs();
  const { isAuthenticated } = useSession();
  const updateProfile = useUpdateProfile();

  useMotionValueEvent(scrollY, "change", (value) => {
    setScrolled(value > 24);
  });

  const hidden = revealOnScroll && !scrolled;
  const isActive = (to: string) => (to === "/" ? pathname === "/" : pathname.startsWith(to));

  const mobileLinkClass = (to: string) => 
    `flex items-center justify-between rounded-2xl px-4 py-3 text-sm transition-colors ${
      isActive(to)
        ? "bg-primary/10 font-semibold text-primary"
        : "text-muted-foreground hover:bg-white/70 hover:text-foreground"
    }`;

  return (
    <motion.header
      initial={false}
      animate={{ y: hidden ? -140 : 0, opacity: hidden ? 0 : 1 }}
      transition={{ type: "spring", stiffness: 260, damping: 30 }}
      className="pointer-events-none sticky top-0 z-50 w-full px-3 py-3 sm:px-6 sm:py-5"
    >
      <div
        className={`pointer-events-auto mx-auto flex w-full max-w-[1400px] items-center justify-between gap-3 rounded-full border border-border/60 bg-background/80 px-3 py-2 backdrop-blur-xl transition-shadow duration-500 sm:px-4 ${
          scrolled
            ? "shadow-[0_26px_60px_-30px_color-mix(in_oklab,var(--primary)_70%,transparent)]"
            : "shadow-[0_14px_40px_-32px_color-mix(in_oklab,var(--primary)_60%,transparent)]"
        }`}
      >
        <Link to="/" className="group flex shrink-0 items-center pl-1">
          <TurnpikeLogo dark={false} />
        </Link>

        <NavigationMenu className="hidden lg:flex max-w-[900px]">
          <NavigationMenuList className="gap-1 flex-wrap justify-center">
            <NavigationMenuItem>
              <Link
                to="/"
                className={`relative rounded-full px-3.5 py-2 text-[13px] font-medium transition-colors duration-300 ${
                  isActive("/") ? "text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {isActive("/") ? (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 -z-10 rounded-full bg-[linear-gradient(140deg,var(--primary),var(--brand-cyan))]"
                  />
                ) : null}
                <span className="relative">Home</span>
              </Link>
            </NavigationMenuItem>

            {/* Services Dropdown */}
            <NavigationMenuItem>
              <NavigationMenuTrigger 
                className={`bg-transparent hover:bg-transparent focus:bg-transparent data-[state=open]:bg-transparent data-[active]:bg-transparent rounded-full px-3.5 py-2 text-[13px] font-medium transition-colors duration-300 ${isActive("/services") ? "text-primary-foreground" : "text-muted-foreground hover:text-foreground data-[state=open]:text-foreground"}`}
              >
                {isActive("/services") ? (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 -z-10 rounded-full bg-[linear-gradient(140deg,var(--primary),var(--brand-cyan))]"
                  />
                ) : null}
                <span className="relative">Services</span>
              </NavigationMenuTrigger>
              <NavigationMenuContent>
                <div className="grid w-[400px] gap-3 p-4 md:w-[600px] md:grid-cols-2 lg:w-[800px] lg:grid-cols-3 bg-background/95 backdrop-blur-xl rounded-2xl border border-border/50 shadow-2xl">
                  {SERVICES.map((item) => (
                    <Link
                      key={item}
                      to="/services"
                      className="block select-none space-y-1 rounded-xl p-3 leading-none no-underline outline-none transition-colors hover:bg-primary/10 hover:text-primary focus:bg-primary/10 focus:text-primary text-sm font-medium"
                    >
                      {item}
                    </Link>
                  ))}
                </div>
              </NavigationMenuContent>
            </NavigationMenuItem>

            {/* Industries Dropdown */}
            <NavigationMenuItem>
              <NavigationMenuTrigger className="bg-transparent hover:bg-transparent focus:bg-transparent data-[state=open]:bg-transparent data-[active]:bg-transparent rounded-full px-3.5 py-2 text-[13px] font-medium transition-colors duration-300 text-muted-foreground hover:text-foreground data-[state=open]:text-foreground">
                <span className="relative">Industries</span>
              </NavigationMenuTrigger>
              <NavigationMenuContent>
                <div className="grid w-[400px] gap-x-2 gap-y-1.5 p-4 md:w-[600px] md:grid-cols-3 lg:w-[900px] lg:grid-cols-4 bg-background/95 backdrop-blur-xl rounded-2xl border border-border/50 shadow-2xl">
                  {INDUSTRIES.map((item) => (
                    <Link
                      key={item}
                      to="/services"
                      className="block select-none rounded-lg p-2 leading-none no-underline outline-none transition-colors hover:bg-primary/10 hover:text-primary focus:bg-primary/10 focus:text-primary text-[13px] font-medium"
                    >
                      {item}
                    </Link>
                  ))}
                </div>
              </NavigationMenuContent>
            </NavigationMenuItem>

            {/* Digital Content Services Dropdown */}
            <NavigationMenuItem>
              <NavigationMenuTrigger className="bg-transparent hover:bg-transparent focus:bg-transparent data-[state=open]:bg-transparent data-[active]:bg-transparent rounded-full px-3.5 py-2 text-[13px] font-medium transition-colors duration-300 text-muted-foreground hover:text-foreground data-[state=open]:text-foreground">
                <span className="relative">Digital Content Services</span>
              </NavigationMenuTrigger>
              <NavigationMenuContent>
                <div className="grid w-[300px] gap-2 p-4 bg-background/95 backdrop-blur-xl rounded-2xl border border-border/50 shadow-2xl">
                  {DIGITAL_CONTENT.map((item) => (
                    <Link
                      key={item}
                      to="/services"
                      className="block select-none rounded-xl p-3 leading-none no-underline outline-none transition-colors hover:bg-primary/10 hover:text-primary focus:bg-primary/10 focus:text-primary text-sm font-medium"
                    >
                      {item}
                    </Link>
                  ))}
                </div>
              </NavigationMenuContent>
            </NavigationMenuItem>

            {/* Software Support Link */}
            <NavigationMenuItem>
              <Link
                to="/services"
                className={`relative rounded-full px-3.5 py-2 text-[13px] font-medium transition-colors duration-300 ${
                  isActive("/software-support") ? "text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <span className="relative">Software Support</span>
              </Link>
            </NavigationMenuItem>

            {/* Training & Courses Dropdown */}
            <NavigationMenuItem>
              <NavigationMenuTrigger 
                className={`bg-transparent hover:bg-transparent focus:bg-transparent data-[state=open]:bg-transparent data-[active]:bg-transparent rounded-full px-3.5 py-2 text-[13px] font-medium transition-colors duration-300 ${isActive("/training") ? "text-primary-foreground" : "text-muted-foreground hover:text-foreground data-[state=open]:text-foreground"}`}
              >
                {isActive("/training") ? (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 -z-10 rounded-full bg-[linear-gradient(140deg,var(--primary),var(--brand-cyan))]"
                  />
                ) : null}
                <span className="relative">Training & Courses</span>
              </NavigationMenuTrigger>
              <NavigationMenuContent>
                <div className="grid w-[250px] gap-2 p-4 bg-background/95 backdrop-blur-xl rounded-2xl border border-border/50 shadow-2xl">
                  {TRAINING.map((item) => (
                    <Link
                      key={item}
                      to="/training"
                      className="block select-none rounded-xl p-3 leading-none no-underline outline-none transition-colors hover:bg-primary/10 hover:text-primary focus:bg-primary/10 focus:text-primary text-sm font-medium"
                    >
                      {item}
                    </Link>
                  ))}
                </div>
              </NavigationMenuContent>
            </NavigationMenuItem>

            {/* Blogs Link */}
            <NavigationMenuItem>
              <Link
                to="/blog"
                className={`relative rounded-full px-3.5 py-2 text-[13px] font-medium transition-colors duration-300 ${
                  isActive("/blog") ? "text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {isActive("/blog") ? (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 -z-10 rounded-full bg-[linear-gradient(140deg,var(--primary),var(--brand-cyan))]"
                  />
                ) : null}
                <span className="relative">Blogs</span>
              </Link>
            </NavigationMenuItem>

            {/* Contact Us Dropdown */}
            <NavigationMenuItem>
              <NavigationMenuTrigger 
                className={`bg-transparent hover:bg-transparent focus:bg-transparent data-[state=open]:bg-transparent data-[active]:bg-transparent rounded-full px-3.5 py-2 text-[13px] font-medium transition-colors duration-300 ${isActive("/contact") ? "text-primary-foreground" : "text-muted-foreground hover:text-foreground data-[state=open]:text-foreground"}`}
              >
                {isActive("/contact") ? (
                  <motion.span
                    layoutId="nav-pill"
                    className="absolute inset-0 -z-10 rounded-full bg-[linear-gradient(140deg,var(--primary),var(--brand-cyan))]"
                  />
                ) : null}
                <span className="relative">Contact Us</span>
              </NavigationMenuTrigger>
              <NavigationMenuContent>
                <div className="grid w-[200px] gap-2 p-4 bg-background/95 backdrop-blur-xl rounded-2xl border border-border/50 shadow-2xl">
                  {CONTACT_US.map((item) => (
                    <Link
                      key={item}
                      to="/contact"
                      className="block select-none rounded-xl p-3 leading-none no-underline outline-none transition-colors hover:bg-primary/10 hover:text-primary focus:bg-primary/10 focus:text-primary text-sm font-medium"
                    >
                      {item}
                    </Link>
                  ))}
                </div>
              </NavigationMenuContent>
            </NavigationMenuItem>
          </NavigationMenuList>
        </NavigationMenu>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              const newDark = !dark;
              setPref("dark", newDark);
              if (isAuthenticated) {
                updateProfile.mutate({ theme: newDark ? "dark" : "light" });
              }
            }}
            className="grid size-10 shrink-0 place-items-center rounded-full border border-border/60 bg-background/60 text-foreground transition-colors hover:text-primary mr-1 sm:mr-2"
          >
            {dark ? <Sun className="size-4.5" /> : <Moon className="size-4.5" />}
          </button>
          
          <button
            type="button"
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((value) => !value)}
            className="grid size-10 place-items-center rounded-full border border-border/60 bg-background/60 text-foreground transition-colors hover:text-primary lg:hidden"
          >
            {open ? <X className="size-5" /> : <Menu className="size-5" />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {open ? (
          <motion.nav
            initial={{ opacity: 0, y: -12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -12, scale: 0.98 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="absolute inset-x-2 top-full mt-2 flex flex-col gap-2 rounded-3xl border border-border/60 bg-background/80 p-3 shadow-xl backdrop-blur-xl lg:hidden max-h-[85vh] overflow-y-auto"
          >
            <Link to="/" onClick={() => setOpen(false)} className={mobileLinkClass("/")}>
              Home <ArrowRight className="size-4 opacity-60" />
            </Link>

            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="services" className="border-b-0">
                <AccordionTrigger className={`px-4 py-3 text-sm hover:no-underline rounded-2xl transition-colors ${isActive("/services") ? "text-primary" : "text-muted-foreground hover:bg-white/70 hover:text-foreground"}`}>
                  Services
                </AccordionTrigger>
                <AccordionContent className="pb-0 pl-4 pr-2">
                  <div className="flex flex-col gap-1 py-2">
                    {SERVICES.map(item => (
                      <Link key={item} to="/services" onClick={() => setOpen(false)} className="px-4 py-2 text-sm text-muted-foreground hover:text-primary">
                        {item}
                      </Link>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
              
              <AccordionItem value="industries" className="border-b-0">
                <AccordionTrigger className="px-4 py-3 text-sm hover:no-underline rounded-2xl transition-colors text-muted-foreground hover:bg-white/70 hover:text-foreground">
                  Industries
                </AccordionTrigger>
                <AccordionContent className="pb-0 pl-4 pr-2">
                  <div className="flex flex-col gap-1 py-2">
                    {INDUSTRIES.map(item => (
                      <Link key={item} to="/services" onClick={() => setOpen(false)} className="px-4 py-2 text-sm text-muted-foreground hover:text-primary">
                        {item}
                      </Link>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="digital" className="border-b-0">
                <AccordionTrigger className="px-4 py-3 text-sm hover:no-underline rounded-2xl transition-colors text-muted-foreground hover:bg-white/70 hover:text-foreground">
                  Digital Content Services
                </AccordionTrigger>
                <AccordionContent className="pb-0 pl-4 pr-2">
                  <div className="flex flex-col gap-1 py-2">
                    {DIGITAL_CONTENT.map(item => (
                      <Link key={item} to="/services" onClick={() => setOpen(false)} className="px-4 py-2 text-sm text-muted-foreground hover:text-primary">
                        {item}
                      </Link>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>

              <Link to="/services" onClick={() => setOpen(false)} className={mobileLinkClass("/software-support")}>
                Software Support <ArrowRight className="size-4 opacity-60" />
              </Link>

              <AccordionItem value="academy" className="border-b-0">
                <AccordionTrigger className={`px-4 py-3 text-sm hover:no-underline rounded-2xl transition-colors ${isActive("/training") ? "text-primary" : "text-muted-foreground hover:bg-white/70 hover:text-foreground"}`}>
                  Training & Courses
                </AccordionTrigger>
                <AccordionContent className="pb-0 pl-4 pr-2">
                  <div className="flex flex-col gap-1 py-2">
                    {TRAINING.map(item => (
                      <Link key={item} to="/training" onClick={() => setOpen(false)} className="px-4 py-2 text-sm text-muted-foreground hover:text-primary">
                        {item}
                      </Link>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="contact" className="border-b-0">
                <AccordionTrigger className={`px-4 py-3 text-sm hover:no-underline rounded-2xl transition-colors ${isActive("/contact") ? "text-primary" : "text-muted-foreground hover:bg-white/70 hover:text-foreground"}`}>
                  Contact Us
                </AccordionTrigger>
                <AccordionContent className="pb-0 pl-4 pr-2">
                  <div className="flex flex-col gap-1 py-2">
                    {CONTACT_US.map(item => (
                      <Link key={item} to="/contact" onClick={() => setOpen(false)} className="px-4 py-2 text-sm text-muted-foreground hover:text-primary">
                        {item}
                      </Link>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>

            </Accordion>

            <Link to="/blog" onClick={() => setOpen(false)} className={mobileLinkClass("/blog")}>
              Blogs <ArrowRight className="size-4 opacity-60" />
            </Link>
          </motion.nav>
        ) : null}
      </AnimatePresence>
    </motion.header>
  );
}
"""

with open('c:/turnpike/frontend/turnpike-insight-suite-main/src/components/site/site-header.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
