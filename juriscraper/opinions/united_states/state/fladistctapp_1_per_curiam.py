
#  Scraper for Florida 1st District Court of Appeal
# CourtID: flaapp1
# Court Short Name: flaapp1
# Author: Andrei Chelaru
# Reviewer: mlr
# History:
# - 20140721: Created.
# - 20140806: Updated by mlr to use Selenium
# - 20140811: Updated by mlr to pass tests when method is 'LOCAL'
# - 20160902: Added helpful exception to let us know when fail is
#   nothing to worry about (current month not available in portal search)


import os
from lxml import html
from selenium import webdriver
from datetime import date, timedelta
from selenium.common.exceptions import NoSuchElementException

from juriscraper.AbstractSite import logger
from juriscraper.OpinionSite import OpinionSite
from juriscraper.AbstractSite import InsanityException


class Site(OpinionSite):
    def __init__(self, *args, **kwargs):
        super(Site, self).__init__(*args, **kwargs)
        self.court_id = self.__module__
        self.case_date = date.today() - timedelta(1)
        self.url = 'https://edca.1dca.org/opinions.aspx'
        self.opinion_type = 'Per Curiam'
        self.release_date = self.case_date.strftime("%m%Y")
        self.uses_selenium = True

    def _download(self, request_dict={}):
        """This is another of the cursed MS asp.net pages with damned POST
          parameters like __EVENTVALIDATION. These are near impossible to
          scrape without using Selenium.
        """
        if self.method == 'LOCAL':
            return super(Site, self)._download(request_dict=request_dict)
        else:
            driver = webdriver.PhantomJS(
                executable_path='/usr/local/phantomjs/phantomjs',
                service_log_path=os.path.devnull,  # Disable ghostdriver.log
                # Without these args, when you get self.url, you'll still be at
                # about:config because the SSL on this site is so terrible.
                service_args=['--ignore-ssl-errors=true',
                              '--ssl-protocol=tlsv1'],
            )
            driver.implicitly_wait(30)
            logger.info("Now downloading case page at: %s" % self.url)
            driver.get(self.url)

            # Select the correct drop downs, then submit.
            path_to_opinion_type = "//select[@id='ddlTypes']/option[@value='{type}']".format(
                type=self.opinion_type)
            driver.find_element_by_xpath(path_to_opinion_type).click()
            path_to_date = "//select[@id='ddlMonths']/option[@value='{d}']".format(
                d=self.release_date)

            try:
                driver.find_element_by_xpath(path_to_date).click()
            except NoSuchElementException:
                # This is not uncommon early in the month (or if there are
                # no opinions published in the current month), so failures
                # resulting from this raise can probably be ignored.
                warning = 'Current month (%s) not yet available in portal--common occurrence early in the month.'
                raise InsanityException(warning % self.release_date)

            path_to_submit = "//input[@id='cmdSearch']"
            driver.find_element_by_xpath(path_to_submit).click()

            # Selenium doesn't give us the actual code, we have to hope.
            self.status = 200

            text = self._clean_text(driver.page_source)
            html_tree = html.fromstring(text)
            html_tree.rewrite_links(self._link_fixer_callback)
        return html_tree

    def _get_case_names(self):
        path = "//*[contains(concat(' ',@id,' '),'_lblDocument')]/text()"
        return list(self.html.xpath(path))

    def _get_download_urls(self):
        path = "//*[contains(concat(' ',@id,' '),'_cmdView')]/@href"
        return list(self.html.xpath(path))

    def _get_case_dates(self):
        path = "count(//*[contains(concat(' ',@id,' '),'_lblCaseNo')])"
        return [self.case_date] * int(self.html.xpath(path))

    def _get_precedential_statuses(self):
        return ['Published'] * len(self.case_names)

    def _get_docket_numbers(self):
        path = "//*[contains(concat(' ',@id,' '),'_lblCaseNo')]/text()"
        return list(self.html.xpath(path))

    def _get_dispositions(self):
        path = "//*[contains(concat(' ',@id,' '),'_lblDisposition')]/text()"
        return list(self.html.xpath(path))
