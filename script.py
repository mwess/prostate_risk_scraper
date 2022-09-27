import argparse
import asyncio
import sys

from playwright.async_api import async_playwright
import pandas as pd


async def main(input_file: str, output_file: str, verbose: bool = False, with_screenshot: bool = False):
    """Parses form parameters from excel file, fills out form and stores resulting risk values. Then writes to the specified output file.

    Args:
        input_file (str): Input file
        output_file (str): Output file
        verbose (bool, optional): Prints to screen if set. Defaults to False.
        with_screenshot (bool, optional): Takes screenshots from every filled out form. Defaults to False.
    """
    df = pd.read_excel(input_file)
    outms = []
    outfs = []
    for idx, row in df.iterrows():

        async with async_playwright() as p:
            url = 'https://darasriskcalcs.shinyapps.io/MSP-RC/'
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url)
            
            # Age
            await page.fill('#age', str(row['age']))
    
            # Assume that DRE == 1 means abnormal
            if row['DRE'] == 1:
                # Select Abnormal in DRE
                await page.wait_for_selector(".well > .form-group:nth-child(2) > div > .selectize-control > .selectize-input")
                await page.click(".well > .form-group:nth-child(2) > div > .selectize-control > .selectize-input")
                await page.locator("xpath=/html/body/div[1]/div/div[1]/form/div[2]/div/div/div[2]").press(key="ArrowDown")
                await page.locator("xpath=/html/body/div[1]/div/div[1]/form/div[2]/div/div/div[2]").press(key="Enter")
    
            # PSA
            await page.locator("xpath=//*[@id=\"psa\"]").fill(str(row['PSA2']))

            # Prostate volume
            await page.locator("xpath=//*[@id=\"mri_vol\"]").fill(str(row['prostatevolume']))

            # PIRADS score
            score = int(row['R_roentgendiagnose'].replace('PIRADS', '')) - 1
            await page.locator("xpath=/html/body/div[1]/div/div[1]/form/div[7]/div/div/div[1]").click()
            i = 0
            while i < score:
                i += 1
                await page.locator("xpath=/html/body/div[1]/div/div[1]/form/div[7]/div/div/div[2]").press(key="ArrowDown")
            await page.locator("xpath=/html/body/div[1]/div/div[1]/form/div[7]/div/div/div[2]").press(key="Enter")

            # previous_neg_biopsy
            # Skip for default
            if row['previous_neg_biopsy'] != 1:
                await page.locator("xpath=/html/body/div[1]/div/div[1]/form/div[8]/div/div/div[1]").click()
                if row['previous_neg_biopsy'] == -1:
                    await page.locator("xpath=/html/body/div[1]/div/div[1]/form/div[8]/div/div/div[1]").press("ArrowDown")
                if row['previous_neg_biopsy'] == 0:
                    await page.locator("xpath=/html/body/div[1]/div/div[1]/form/div[8]/div/div/div[1]").press("ArrowDown")
                    await page.locator("xpath=/html/body/div[1]/div/div[1]/form/div[8]/div/div/div[1]").press("ArrowDown")
                await page.locator("xpath=/html/body/div[1]/div/div[1]/form/div[8]/div/div/div[1]").press('Enter')


            # famhist
            if row['fam_hist_imputed'] == 1:
                await page.locator("xpath=/html/body/div[1]/div/div[1]/form/div[4]/div/div/div[1]").press("ArrowDown")
                await page.locator("xpath=/html/body/div[1]/div/div[1]/form/div[4]/div/div/div[1]").press("Enter")

            # Patient AA
            #if row['Is patient AA'] != 'no':
            #    await page.locator("xpath=/html/body/div[1]/div/div[1]/form/div[3]/div/div/div[1]").press("ArrowDown")
            #    await page.locator("xpath=/html/body/div[1]/div/div[1]/form/div[3]/div/div/div[1]").press("Enter")


            await page.wait_for_timeout(2000);
    

            outm = (await page.locator("#outm").all_inner_texts())
            outf = (await page.locator("#outf").all_inner_texts())
            
            outms.append(outm[0])
            outfs.append(outf[0])
            if verbose:
                print(idx)
                print(f'outm: {outm[0]}')
                print(f'outf: {outf[0]}')

            if with_screenshot:    
                await page.screenshot(path=f'{idx}.png')

            await browser.close()
            
    df['risk_positive_biopsy'] = outms
    df['risk_clinically_sign_biopsy'] = outfs
    df.to_excel(output_file)

    
def parse_arguments():
    
    parser = argparse.ArgumentParser(description="Parses webform. ")
    parser.add_argument('--input', type=str, help='Input file.')
    parser.add_argument('--output', type=str, help='Output file.')
    parser.add_argument('--verbose', const=False, default=False, type=bool, nargs='?', help='Prints out parsed risks for every row if true.')
    parser.add_argument('--screenshot', const=False, default=True, type=bool, nargs='?', help='Takes screenshots of every parsed row.')
    args = parser.parse_args()
    return args
        
if __name__ == "__main__":
    args = parse_arguments()
    asyncio.run(main(input_file=args.input, output_file=args.output, verbose=args.verbose, with_screenshot=args.screenshot))
