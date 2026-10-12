import React from "react";
import { createRoot } from "react-dom/client";
import { ProductDataProvider } from "../../src/context/ProductDataContext";
import { CraftStudio } from "../../src/studios/craft/CraftStudio";

const host = document.getElementById("root")!;
createRoot(host).render(<ProductDataProvider><CraftStudio /></ProductDataProvider>);
